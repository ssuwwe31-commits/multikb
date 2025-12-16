"""
Diagnosis orchestration service.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import traceback

from sqlalchemy.orm import Session  # type: ignore

from app.config.settings import settings
from app.core.logging import logger
from app.models.cluster_config import ClusterConfig
from app.schemas.observability import DiagnosisRecordResponse, DiagnosisFeedbackRequest
from app.services.cluster_config_service import ClusterConfigService, DiagnosisRecordService
from app.services.search_service import SearchService
from app.services.diagnosis_rule_service import DiagnosisRuleService
from app.services.ollama_service import OllamaService
from app.services.diagnosis_iteration_service import DiagnosisIterationService, DiagnosisMemoryService
from app.services.opensearch_service import OpenSearchService
from app.services.diagnosis_data_collector import DiagnosisDataCollector
from app.services.diagnosis_llm_service import DiagnosisLlmService
from app.services.diagnosis_k8s_collector import DiagnosisK8sCollector
from app.services.diagnosis_report_service import DiagnosisReportService
from app.services.diagnosis_summary_service import DiagnosisSummaryService
from app.services.resource_event_service import ResourceEventService
from app.tasks.celery_app import celery_app


class DiagnosisService:
    """Coordinates observability data and knowledge base to produce diagnosis records."""

    def __init__(self, db: Session):
        self.db = db
        self.cluster_service = ClusterConfigService(db)
        self.record_service = DiagnosisRecordService(db)
        self.search_service = SearchService(db)
        self.rule_service = DiagnosisRuleService()
        self.ollama_service = OllamaService(db)
        self.iteration_service = DiagnosisIterationService(db)
        self.memory_service = DiagnosisMemoryService(db)
        self.opensearch_service = OpenSearchService()
        self.resource_event_service = ResourceEventService(db)
        
        # 初始化拆分后的服务模块
        self.data_collector = DiagnosisDataCollector(db, self.search_service)
        self.llm_service = DiagnosisLlmService(db, self.ollama_service, self.rule_service)
        self.k8s_collector = DiagnosisK8sCollector(db, self.record_service, self.memory_service)
        self.report_service = DiagnosisReportService(self.memory_service, self.iteration_service, self.opensearch_service)
        self.summary_service = DiagnosisSummaryService()

    async def trigger_diagnosis(
        self,
        cluster_id: int,
        namespace: Optional[str],
        resource_type: str,
        resource_name: str,
        trigger_source: str = "manual",
        trigger_payload: Optional[Dict[str, Any]] = None,
        time_range_hours: Optional[float] = None,
    ) -> DiagnosisRecordResponse:
        cluster = await self.cluster_service.get(cluster_id)
        if not cluster:
            raise ValueError("Cluster not found")

        runtime = self.cluster_service.build_runtime_payload(cluster)
        # 默认使用 2.0 小时（120分钟），如果没有传入则使用默认值
        if time_range_hours is None:
            time_range_hours = 2.0
        context = {
            "cluster_id": cluster_id,
            "namespace": namespace,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "time_range_hours": time_range_hours,  # 将时间范围传入 context
        }
        record = await self.record_service.create_record(
            {
                "cluster_id": cluster_id,
                "namespace": namespace,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "trigger_source": trigger_source,
                "trigger_payload": trigger_payload,
                "symptoms": context,
                "status": "running",
                "summary": "诊断进行中",
                "conclusion": "",
                "confidence": 0.0,
                "metrics": {},
                "logs": {},
                "recommendations": {},
                "knowledge_refs": None,
                "knowledge_source": None,
                "events": [self._make_event("start", "诊断开始", "info")],
            }
        )

        iteration_result = await self._execute_iteration(
            record=record,
            cluster=cluster,
            runtime=runtime,
            context=context,
            trigger_source=trigger_source,
            trigger_payload=trigger_payload,
        )

        if iteration_result.get("status") == "pending_next":
            self._schedule_next_iteration(record.id)

        record_with_relations = await self.record_service.get_with_relations(record.id)
        return DiagnosisRecordResponse.model_validate(record_with_relations or record)

    async def continue_diagnosis(self, record_id: int) -> Optional[DiagnosisRecordResponse]:
        record = await self.record_service.get(record_id)
        if not record or record.is_deleted:
            return None
        if record.status in ("completed", "failed", "pending_human"):
            return DiagnosisRecordResponse.model_validate(record)

        cluster = await self.cluster_service.get(record.cluster_id)
        if not cluster:
            await self.record_service.append_event(
                record.id,
                self._make_event("error", "无法继续诊断: 集群不存在", "error"),
            )
            await self.record_service.update_status(record.id, "failed")
            return DiagnosisRecordResponse.model_validate(record)

        runtime = self.cluster_service.build_runtime_payload(cluster)
        context = {
            "cluster_id": record.cluster_id,
            "namespace": record.namespace,
            "resource_type": record.resource_type or "pods",
            "resource_name": record.resource_name,
        }

        iteration_result = await self._execute_iteration(
            record=record,
            cluster=cluster,
            runtime=runtime,
            context=context,
            trigger_source=record.trigger_source or "manual",
            trigger_payload=record.trigger_payload,
        )

        # 注意：根据设计文档，单轮迭代内已完成所有9个诊断步骤，不再进行多轮迭代
        # 如果置信分<0.8，状态为pending_human，需要人工介入
        # 不再自动调度下一轮迭代

        record_with_relations = await self.record_service.get_with_relations(record.id)
        return DiagnosisRecordResponse.model_validate(record_with_relations or record)

    async def process_feedback(self, record_id: int, payload: DiagnosisFeedbackRequest) -> DiagnosisRecordResponse:
        record = await self.record_service.get_with_relations(record_id)
        if not record or record.is_deleted:
            raise ValueError("诊断记录不存在")

        iteration_no = payload.iteration_no
        if not iteration_no:
            iteration_no = record.iterations[-1].iteration_no if record.iterations else 1
        iteration = self._find_iteration_by_no(record, iteration_no)
        executed_step = self._extract_highest_completed_step(iteration.action_result if iteration else None)
        if executed_step <= 0:
            executed_step = 1

        feedback_entry = {
            "feedback_type": payload.feedback_type,
            "feedback_notes": (payload.feedback_notes or "").strip() or None,
            "action_taken": (payload.action_taken or "").strip() or None,
            "iteration_no": iteration_no,
            "continue_from_step": executed_step if payload.feedback_type == "continue_investigation" else None,
            "submitted_at": datetime.utcnow().isoformat() + "Z",
        }

        state_updates = {
            "last_feedback_type": payload.feedback_type,
            "last_feedback_iteration": iteration_no,
        }
        min_steps_before_exit = None
        if payload.feedback_type == "continue_investigation":
            min_steps_before_exit = 3
            state_updates.update(
                {
                    "continue_from_step": executed_step,
                    "min_steps_before_exit": min_steps_before_exit,
                }
            )

        record = await self.record_service.save_feedback(
            record_id,
            feedback_entry,
            state_updates=state_updates,
            record=record,
        )

        message_suffix = payload.feedback_notes.strip() if payload.feedback_notes else "无"
        await self.record_service.append_event(
            record.id,
            self._make_event(
                "feedback",
                f"[迭代 {iteration_no}] 收到反馈（{payload.feedback_type}）：{message_suffix}",
                "info",
            ),
        )

        # 记录反馈到记忆
        await self.memory_service.add_memory(
            record.id,
            memory_type="feedback",
            summary=f"[迭代 {iteration_no}] 用户反馈：{payload.feedback_type}",
            content=feedback_entry,
            iteration_id=iteration.id if iteration else None,
            iteration_no=iteration_no,
        )

        if payload.feedback_type == "confirmed":
            await self._handle_feedback_confirmed(record)
        elif payload.feedback_type == "continue_investigation":
            await self._handle_feedback_continue(
                record,
                continue_from_step=executed_step,
                min_steps_before_exit=min_steps_before_exit or 3,
                notes=payload.feedback_notes,
            )

        record_with_relations = await self.record_service.get_with_relations(record.id)
        return DiagnosisRecordResponse.model_validate(record_with_relations or record)

    async def _run_single_iteration(
        self,
        record: Any,
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
        context: Dict[str, Any],
        iteration: Any,
        trigger_source: str,
        trigger_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        namespace = context.get("namespace")
        resource_name = context.get("resource_name")
        iteration_no = iteration.iteration_no

        action_plan: List[Dict[str, Any]] = [
            {"name": "collect_data", "description": "统一数据收集（API Server + 监控系统 + 日志系统）"},
            {"name": "rule_evaluate", "description": "执行规则引擎"},
            {"name": "step1_llm_analysis_with_data", "description": "第一步：基于实际数据的模型分析 ⭐【核心改进】"},
            {"name": "step2_generate_problem_description", "description": "第二步：生成问题描述（用于知识库搜索，条件触发）"},
            {"name": "step3_search_knowledge", "description": "第三步：搜索知识库（条件触发）"},
            {"name": "step4_evaluate_knowledge", "description": "第四步：评估知识库内容准确性（条件触发）"},
            {"name": "step5_expand_k8s_resources", "description": "第五步：扩展K8s信息收集（第一层扩展，条件触发）"},
            {"name": "step6_llm_analysis_with_k8s", "description": "第六步：基于扩展K8s信息的模型分析（条件触发）"},
            {"name": "step7_search_external", "description": "第七步：外部搜索（条件触发）"},
            {"name": "step8_llm_final_with_external", "description": "第八步：基于外部搜索结果的模型分析（条件触发）"},
        ]

        action_results: List[Dict[str, Any]] = []
        min_steps_before_exit = max(1, int(context.get("min_steps_before_exit") or 1))
        feedback_continue_from_step = context.get("feedback_continue_from_step")
        if min_steps_before_exit > 1:
            raw_prev_iteration = context.get("last_feedback_iteration")
            if isinstance(raw_prev_iteration, int) and raw_prev_iteration > 0:
                previous_iteration_label = f"{raw_prev_iteration}"
            else:
                previous_iteration_label = f"{iteration_no - 1}" if iteration_no > 1 else "?"
            await self.record_service.append_event(
                record.id,
                self._make_event(
                    "feedback_followup",
                    (
                        f"[迭代 {iteration_no}] 上一轮（第{previous_iteration_label}轮）人工反馈要求继续排查，"
                        f"上一轮执行到第 {feedback_continue_from_step or 1} 步，本轮必须至少执行到第 {min_steps_before_exit} 步后才能结束。"
                    ),
                    "info",
                ),
            )

        await self.record_service.append_event(
            record.id,
            self._make_event("iteration", f"迭代 {iteration_no} 开始执行动作计划", "info"),
        )

        resource_type = context.get("resource_type", "pods")
        
        await self.record_service.append_event(
            record.id,
            self._make_event("collect_data", f"[迭代 {iteration_no}] 开始收集数据（统一入口）", "info"),
        )
        # 优先使用 context 中传入的时间范围，否则检查是否需要使用更长的时间范围（深度诊断）
        time_range_hours = context.get("time_range_hours")
        logger.warning(
            f"[诊断流程] 开始数据收集: 资源={resource_type}/{resource_name}, "
            f"命名空间={namespace}, 传入时间范围={time_range_hours}"
        )
        if time_range_hours is None:
            # 默认使用 2.0 小时（120分钟）
            time_range_hours = 2.0
            logger.warning(f"[诊断流程] 使用默认时间范围: {time_range_hours}小时")
            # 检查是否有深度上下文记忆，如果有则使用更长的时间范围
            memories = await self.memory_service.list_by_diagnosis(record.id)
            for memory in memories:
                if memory.memory_type == "deep_context":
                    time_range_hours = 4.0  # 深度诊断使用 4 小时
                    logger.warning(f"[诊断流程] 检测到深度上下文，使用时间范围: {time_range_hours}小时")
                    break
        
        logger.warning(
            f"[诊断流程] 调用 collect_data: 资源={resource_type}/{resource_name}, "
            f"命名空间={namespace}, 集群={cluster.name if cluster else 'N/A'}, "
            f"时间范围={time_range_hours}小时"
        )
        
        # 使用统一的数据收集方法
        try:
            data = await self.data_collector.collect_data(
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
                cluster=cluster,
                runtime=runtime,
                time_range_hours=time_range_hours,
            )
            logger.warning(
                f"[诊断流程] collect_data 完成: 指标keys={list(data.get('metrics', {}).keys())}, "
                f"日志数量={len(data.get('logs', {}).get('logs', []))}"
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"[诊断流程] collect_data 失败: {exc}", exc_info=True)
            raise
        
        api_data = data.get("api_data", {})
        metrics_data = data.get("metrics", {})
        logs_data = data.get("logs", {})
        
        await self.record_service.append_event(
            record.id,
            self._make_event("collect_data", f"[迭代 {iteration_no}] 数据收集完成", "success"),
        )
        action_results.append(
            {
                "name": "collect_data",
                "status": "success",
                "details": {
                    "api_data": bool(api_data),
                    "metrics": list(metrics_data.keys()),
                    "logs": len(logs_data.get("logs", [])) if isinstance(logs_data, dict) else 0,
                },
            }
        )
        
        # 保存 API 数据到记忆
        if api_data:
            await self.memory_service.add_memory(
                record.id,
                memory_type="api_data",
                summary=f"[迭代 {iteration_no}] API Server 数据：资源状态和配置已收集",
                content=api_data,
                iteration_id=iteration.id,
                iteration_no=iteration_no,
            )
        
        # 从 api_data 中提取配置信息并存储到 symptoms.config
        if api_data and isinstance(api_data, dict):
            config_data = self._extract_config_from_api_data(api_data, resource_type)
            if config_data:
                # 更新 record.symptoms 中的 config
                # 使用深拷贝确保不会丢失已有数据
                import copy
                current_symptoms = copy.deepcopy(record.symptoms) if record.symptoms and isinstance(record.symptoms, dict) else {}
                if not current_symptoms.get("config"):
                    current_symptoms["config"] = config_data
                    record.symptoms = current_symptoms
                    # 不需要立即提交，会在迭代结束时统一提交
                    logger.warning(
                        f"[诊断流程] 从 api_data 提取配置信息并存储到 symptoms.config: "
                        f"键数量={len(config_data)}, 键列表={list(config_data.keys())[:5]}, "
                        f"symptoms 总键数={len(current_symptoms)}, symptoms 键列表={list(current_symptoms.keys())[:10]}"
                    )
                else:
                    logger.warning(
                        f"[诊断流程] symptoms.config 已存在，跳过更新。现有键数量={len(current_symptoms.get('config', {}))}"
                    )
        
        # 保存指标数据到记忆
        if metrics_data:
            await self.memory_service.add_memory(
                record.id,
                memory_type="metric",
                summary=self.summary_service.generate_metric_summary(metrics_data, iteration_no),
                content=metrics_data,
                iteration_id=iteration.id,
                iteration_no=iteration_no,
            )
        
        # 保存日志数据到记忆
        if logs_data:
            await self.memory_service.add_memory(
                record.id,
                memory_type="log",
                summary=self.summary_service.generate_log_summary(logs_data, iteration_no),
                content=logs_data,
                iteration_id=iteration.id,
                iteration_no=iteration_no,
            )

        # 查询最近的资源变更信息（问题发生前 24 小时）
        recent_changes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            # 获取资源的 UID（如果 api_data 中有）
            resource_uid = None
            if api_data and isinstance(api_data, dict):
                metadata = api_data.get("metadata", {})
                resource_uid = metadata.get("uid")
            
            # 查询相关资源的变更事件
            # 1. 查询目标资源本身的变更
            if resource_uid:
                changes = await self.resource_event_service.query_events(
                    cluster_id=cluster.id,
                    resource_type=resource_type,
                    namespace=namespace,
                    resource_uid=resource_uid,
                    start_time=start_time,
                    end_time=end_time,
                    limit=50,
                )
                recent_changes.extend(changes)
            
            # 2. 查询同一命名空间的相关资源变更（ConfigMap、Secret、Deployment 等）
            related_resource_types = ["configmaps", "secrets", "deployments", "statefulsets", "daemonsets"]
            for related_type in related_resource_types:
                if related_type != resource_type:
                    changes = await self.resource_event_service.query_events(
                        cluster_id=cluster.id,
                        resource_type=related_type,
                        namespace=namespace,
                        start_time=start_time,
                        end_time=end_time,
                        limit=20,  # 每种资源类型最多 20 条
                    )
                    # 只保留 updated 和 created 事件（配置变更）
                    filtered_changes = [c for c in changes if c.get("event_type") in ["updated", "created"]]
                    recent_changes.extend(filtered_changes)
            
            # 按时间排序，最新的在前
            recent_changes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            # 限制总数，避免数据过多
            recent_changes = recent_changes[:100]
            
            if recent_changes:
                await self.record_service.append_event(
                    record.id,
                    self._make_event(
                        "change_analysis",
                        f"[迭代 {iteration_no}] 发现 {len(recent_changes)} 条最近变更记录",
                        "info",
                    ),
                )
                # 保存变更信息到记忆
                await self.memory_service.add_memory(
                    record.id,
                    memory_type="change_event",
                    summary=f"[迭代 {iteration_no}] 最近 24 小时发现 {len(recent_changes)} 条资源变更",
                    content={"changes": recent_changes, "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()}},
                    iteration_id=iteration.id,
                    iteration_no=iteration_no,
                )
        except Exception as exc:
            logger.warning(f"查询资源变更信息失败: {exc}")
            # 不影响主流程，继续执行

        # 规则检测（传递 resource_type 和 api_data）
        rule_findings = self.rule_service.evaluate(resource_type, context, api_data, metrics_data, logs_data)
        if rule_findings:
            await self.record_service.append_event(
                record.id,
                self._make_event("rule_engine", f"[迭代 {iteration_no}] 命中规则 {len(rule_findings)} 项", "warning"),
            )
        else:
            await self.record_service.append_event(
                record.id,
                self._make_event("rule_engine", f"[迭代 {iteration_no}] 规则检查未命中", "info"),
            )
        action_results.append(
            {
                "name": "rule_evaluate",
                "status": "hit" if rule_findings else "none",
                "details": {"count": len(rule_findings)},
            }
        )
        if rule_findings:
            await self.memory_service.add_memory(
                record.id,
                memory_type="rule",
                summary=self.summary_service.generate_rule_summary(rule_findings, iteration_no),
                content=rule_findings,
                iteration_id=iteration.id,
                iteration_no=iteration_no,
            )

        # 获取已收集的变更信息（如果有）
        change_events = None
        memories = await self.memory_service.list_by_diagnosis(record.id)
        for memory in memories:
            if memory.memory_type == "change_event":
                change_events = memory.content
        
        # 定义置信度阈值（在函数开始处定义，供后续所有步骤使用）
        confidence_threshold = settings.OBSERVABILITY_DIAGNOSIS_CONFIDENCE_THRESHOLD
        
        # ========== 第一步：基于实际数据的模型分析 ⭐【核心改进】==========
        # **关键改进**：收集数据后，立即让模型分析实际数据，判断问题，给出置信分
        # 如果置信分 >= 0.8，直接完成诊断，跳过后续步骤（知识库搜索等）
        # 如果置信分 < 0.8，继续执行后续步骤（搜索知识库、扩展信息等）
        llm_confidence_step1: float = 0.0
        llm_result_step1: Optional[Dict[str, Any]] = None
        
        if settings.OLLAMA_MODEL:
            await self.record_service.append_event(
                record.id,
                self._make_event("step1_llm_analysis_with_data", f"[迭代 {iteration_no}] 开始基于实际数据的模型分析 ⭐【核心改进】", "info"),
            )
            prior_memories_step1 = await self._get_prior_memories_for_llm(record.id, iteration_no)
            
            # 调用 LLM 分析实际数据
            # 传入收集的基础数据（指标、日志、规则检测结果、API数据、变更事件）
            # 不传入知识库内容和外部搜索结果（这是第一步，还没有搜索知识库）
            llm_result_step1 = await self.llm_service.call_llm(
                context, metrics_data, logs_data, rule_findings, None, None,  # knowledge_refs=None, external_refs=None
                None, None, prior_memories_step1, api_data, change_events, resource_type  # k8s_resources=None, deep_context=None
            )
            
            # 提取置信度
            if isinstance(llm_result_step1, dict) and "confidence" in llm_result_step1:
                llm_confidence_step1 = float(llm_result_step1.get("confidence", 0.0))
            else:
                llm_confidence_step1 = 0.3
            
            logger.info(
                f"[诊断流程][第一步] 基于实际数据的模型分析完成: 置信分={llm_confidence_step1:.2%}, "
                f"阈值={confidence_threshold:.2%}"
            )
            
            await self.record_service.append_event(
                record.id,
                self._make_event(
                    "step1_llm_analysis_with_data",
                    f"[迭代 {iteration_no}] 基于实际数据的模型分析完成（置信度: {llm_confidence_step1:.2%}）",
                    "success" if llm_result_step1 else "info",
                ),
            )
            action_results.append(
                {
                    "name": "step1_llm_analysis_with_data",
                    "status": "success" if llm_result_step1 else "empty",
                    "details": {"confidence": llm_confidence_step1},
                }
            )
            
            # 保存到记忆
            if llm_result_step1:
                await self.memory_service.add_memory(
                    record.id,
                    memory_type="llm",
                    summary=f"[迭代 {iteration_no}] 第一步：基于实际数据的模型分析完成（置信度: {llm_confidence_step1:.2%}）",
                    content=llm_result_step1,
                    iteration_id=iteration.id,
                    iteration_no=iteration_no,
                )
            
            shortcut_allowed = llm_confidence_step1 >= confidence_threshold and min_steps_before_exit <= 1
            # **关键逻辑**：如果第一步置信分 >= 0.8 且允许跳出，直接完成诊断
            if shortcut_allowed:
                logger.info(
                    f"[诊断流程][第一步] ✅ 模型分析置信分{llm_confidence_step1:.2%}>=阈值{confidence_threshold:.2%}，"
                    f"直接完成诊断，跳过后续步骤（第二步到第八步）"
                )
                # 跳过后续所有步骤
                action_results.append({"name": "step2_generate_problem_description", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
                action_results.append({"name": "step3_search_knowledge", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
                action_results.append({"name": "step4_evaluate_knowledge", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
                action_results.append({"name": "step5_expand_k8s_resources", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
                action_results.append({"name": "step6_llm_analysis_with_k8s", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
                action_results.append({"name": "step7_search_external", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
                action_results.append({"name": "step8_llm_final_with_external", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
                
                # 设置最终结果
                knowledge_refs = None
                knowledge_confidence = 0.0
                k8s_resources = None
                external_refs = None
                llm_result = llm_result_step1
                llm_confidence = llm_confidence_step1
                problem_summary = ""
                enhanced_problem_summary = ""
            else:
                if llm_confidence_step1 < confidence_threshold:
                    logger.info(
                        f"[诊断流程][第一步] ⚠️ 模型分析置信分{llm_confidence_step1:.2%}<阈值{confidence_threshold:.2%}，"
                        f"将继续执行后续步骤（第二步到第八步）"
                    )
                else:
                    logger.info(
                        f"[诊断流程][第一步] 置信分{llm_confidence_step1:.2%}>=阈值{confidence_threshold:.2%}，"
                        f"但根据人工反馈要求继续执行到第 {min_steps_before_exit} 步"
                    )
        else:
            # LLM未启用，跳过第一步
            logger.warning(f"[诊断流程][第一步] LLM未启用，跳过基于实际数据的模型分析")
            action_results.append({"name": "step1_llm_analysis_with_data", "status": "skipped", "details": {"reason": "LLM未启用"}})
            llm_confidence_step1 = 0.0
        
        # ========== 第二步：生成问题描述（用于知识库搜索，条件触发）==========
        # **触发条件**：第一步的模型分析置信分 < 0.8
        # **跳过条件**：如果第一步置信分 >= 0.8，跳过此步骤（已在上面处理）
        problem_summary = ""
        
        if llm_confidence_step1 < confidence_threshold or min_steps_before_exit >= 2:
            # 检查规则引擎是否明确识别出问题类型（快速路径）
            rule_identified_problem = None
            if rule_findings:
                # 检查是否有明确的规则匹配（如CPU_THRESHOLD、MEMORY_THRESHOLD、RESTART_THRESHOLD等）
                for finding in rule_findings:
                    rule = finding.get("rule", "")
                    if rule in ["CPU_THRESHOLD", "MEMORY_THRESHOLD", "RESTART_THRESHOLD", "POD_CRASHLOOPBACKOFF", 
                               "POD_IMAGEPULLBACKOFF", "POD_UNHEALTHY"]:
                        # 基于规则类型生成问题描述
                        rule_identified_problem = {
                            "type": rule,
                            "message": finding.get("message", ""),
                        }
                        break
            
            if rule_identified_problem:
                # 路径A：规则引擎明确识别 → 基于问题类型生成问题描述（快速路径）
                problem_summary = f"{rule_identified_problem['message']} - {resource_type} {resource_name} 在命名空间 {namespace}"
                await self.record_service.append_event(
                    record.id,
                    self._make_event("step2_generate_problem_description", 
                                   f"[迭代 {iteration_no}] 规则引擎识别问题: {rule_identified_problem['type']}", "info"),
                )
                action_results.append(
                    {
                        "name": "step2_generate_problem_description",
                        "status": "rule_identified",
                        "details": {"problem_type": rule_identified_problem['type'], "problem_summary": problem_summary[:200]},
                    }
                )
            else:
                # 路径B：规则引擎无法明确识别 → LLM 生成问题总结
                if settings.OLLAMA_MODEL:
                    await self.record_service.append_event(
                        record.id,
                        self._make_event("step2_generate_problem_description", f"[迭代 {iteration_no}] LLM 开始生成问题总结（用于知识库搜索）", "info"),
                    )
                    try:
                        # 基于收集到的数据（指标、日志、规则检测结果、API数据、变更事件、第一步的模型分析结果）
                        problem_summary = await self.llm_service.generate_problem_summary(
                            context, metrics_data, logs_data, rule_findings, api_data, change_events, resource_type
                        )
                        # 如果第一步有模型分析结果，可以结合使用
                        if llm_result_step1 and isinstance(llm_result_step1, dict):
                            problem_desc = llm_result_step1.get("problem_description", "")
                            if problem_desc and problem_desc not in problem_summary:
                                problem_summary = f"{problem_summary} {problem_desc}".strip()
                        
                        await self.record_service.append_event(
                            record.id,
                            self._make_event("step2_generate_problem_description", f"[迭代 {iteration_no}] LLM 问题总结生成完成", "success"),
                        )
                        action_results.append(
                            {
                                "name": "step2_generate_problem_description",
                                "status": "llm_generated",
                                "details": {"problem_summary": problem_summary[:200]},
                            }
                        )
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning(f"生成问题总结失败: {exc}")
                        problem_summary = f"{resource_type} {resource_name} 在命名空间 {namespace} 出现问题"
                        action_results.append({"name": "step2_generate_problem_description", "status": "failed", "details": {"error": str(exc)}})
                else:
                    # 没有 LLM，使用简单描述
                    problem_summary = f"{resource_type} {resource_name} 在命名空间 {namespace} 出现问题"
                    action_results.append({"name": "step2_generate_problem_description", "status": "simple", "details": {"reason": "LLM未启用"}})
        else:
            # 第一步置信分 >= 0.8，跳过此步骤
            action_results.append({"name": "step2_generate_problem_description", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
        
        # ========== 第三步：搜索知识库（条件触发）==========
        # **触发条件**：第一步的模型分析置信分 < 0.8
        # **跳过条件**：如果第一步置信分 >= 0.8，跳过此步骤（已在上面处理）
        knowledge_refs: Optional[List[Dict[str, Any]]] = None
        knowledge_confidence: float = 0.0
        
        if llm_confidence_step1 < confidence_threshold or min_steps_before_exit >= 3:
            if problem_summary:
                knowledge_refs = await self.data_collector.search_knowledge(problem_summary)
            await self.record_service.append_event(
                record.id,
                self._make_event(
                    "step3_search_knowledge",
                    f"[迭代 {iteration_no}] 知识库检索{'命中' if knowledge_refs else '未命中'}",
                    "success" if knowledge_refs else "info",
                ),
            )
            action_results.append(
                {
                    "name": "step3_search_knowledge",
                    "status": "found" if knowledge_refs else "not_found",
                    "details": {"count": len(knowledge_refs) if knowledge_refs else 0},
                }
            )
            # 保存到记忆（符合设计文档要求：第三步保存到记忆 memory_type: knowledge）
            if knowledge_refs:
                await self.memory_service.add_memory(
                    record.id,
                    memory_type="knowledge",
                    summary=f"[迭代 {iteration_no}] 第三步：搜索知识库找到 {len(knowledge_refs)} 个相关文档",
                    content={"knowledge_refs": knowledge_refs},
                    iteration_id=iteration.id,
                    iteration_no=iteration_no,
                )
        else:
            # 第一步置信分 >= 0.8，跳过此步骤
            action_results.append({"name": "step3_search_knowledge", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})

        # ========== 第四步：评估知识库内容准确性（条件触发）==========
        # **触发条件**：第三步搜索知识库后找到结果
        # **跳过条件**：如果第三步未搜索到结果，跳过此步骤
        if llm_confidence_step1 < confidence_threshold:
            if knowledge_refs and settings.OLLAMA_MODEL:
                await self.record_service.append_event(
                    record.id,
                    self._make_event("step4_evaluate_knowledge", f"[迭代 {iteration_no}] 开始评估知识库内容准确度", "info"),
                )
                total_docs = len(knowledge_refs)
                max_eval_docs = max(1, settings.OBSERVABILITY_KNOWLEDGE_EVAL_MAX_DOCS)
                docs_to_evaluate = knowledge_refs[:max_eval_docs]
                if total_docs > max_eval_docs:
                    logger.info(
                        f"[诊断流程][第四步] 开始评估知识库内容，共 {total_docs} 个文档，本次仅评估排名靠前的 {max_eval_docs} 个候选"
                    )
                else:
                    logger.info(f"[诊断流程][第四步] 开始评估知识库内容，共 {total_docs} 个文档")
                
                # 评估所有知识库文档，取最高置信分
                best_confidence = 0.0
                best_doc = None
                relevant_docs = []
                
                for idx, doc in enumerate(docs_to_evaluate, 1):
                    doc_content = doc.get("content", "")
                    # 安全提取文档标题，确保转换为字符串（document_id可能是整数）
                    doc_title = str(doc.get("title") or doc.get("name") or doc.get("document_id") or "").strip()
                    if not doc_title:
                        doc_title = doc_content[:50].strip() or "未命名文档"
                    if doc_content:
                        eval_result = await self.llm_service.evaluate_knowledge_relevance(
                            problem_summary, doc_content, context
                        )
                        doc_confidence = float(eval_result.get("confidence", 0.0))
                        is_relevant = eval_result.get("is_relevant", False)
                        
                        logger.info(
                            f"[诊断流程][第四步] 文档 {idx}/{len(docs_to_evaluate)} 评估完成: "
                            f"标题={doc_title}, 相关性={is_relevant}, 置信分={doc_confidence:.2%}"
                        )
                        
                        if is_relevant and doc_confidence > best_confidence:
                            best_confidence = doc_confidence
                            best_doc = {**doc, "evaluation": eval_result}
                            logger.info(
                                f"[诊断流程][第四步] 更新最高置信分: {best_confidence:.2%} "
                                f"(文档: {doc_title})"
                            )
                        
                        if is_relevant:
                            relevant_docs.append({**doc, "evaluation": eval_result})
                
                knowledge_confidence = best_confidence
                logger.info(
                    f"[诊断流程][第四步] 知识库评估完成: 相关文档数={len(relevant_docs)}, "
                    f"最高置信分={knowledge_confidence:.2%}, 阈值={confidence_threshold:.2%}"
                )
                
                if relevant_docs:
                    knowledge_refs = relevant_docs
                    knowledge_evaluation = {
                        "relevant_count": len(relevant_docs),
                        "best_confidence": best_confidence,
                        "best_doc": best_doc,
                    }
                    await self.memory_service.add_memory(
                        record.id,
                        memory_type="knowledge",
                        summary=f"[迭代 {iteration_no}] 第四步：评估知识库找到 {len(relevant_docs)} 个相关条目，最高置信分: {best_confidence:.2%}",
                        content={"knowledge_refs": relevant_docs, "evaluation": knowledge_evaluation},
                        iteration_id=iteration.id,
                        iteration_no=iteration_no,
                    )
                    action_results.append(
                        {
                            "name": "step4_evaluate_knowledge",
                            "status": "relevant",
                            "details": {
                                "relevant_count": len(relevant_docs),
                                "best_confidence": best_confidence,
                            },
                        }
                    )
                    # 如果知识库置信分 >= 0.8，直接完成诊断，跳过后续步骤
                    confidence_threshold_temp = settings.OBSERVABILITY_DIAGNOSIS_CONFIDENCE_THRESHOLD
                    if knowledge_confidence >= confidence_threshold_temp:
                        logger.info(
                            f"[诊断流程][第四步] ✅ 知识库置信分{knowledge_confidence:.2%}>=阈值{confidence_threshold:.2%}，"
                            f"直接完成诊断，跳过后续步骤（第五步到第八步）"
                        )
                        action_results.append({"name": "step5_expand_k8s_resources", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
                        action_results.append({"name": "step6_llm_analysis_with_k8s", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
                        action_results.append({"name": "step7_search_external", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
                        action_results.append({"name": "step8_llm_final_with_external", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
                    else:
                        logger.info(
                            f"[诊断流程][第四步] ⚠️ 知识库置信分{knowledge_confidence:.2%}<阈值{confidence_threshold:.2%}，"
                            f"将继续执行后续步骤（第五步到第八步）"
                        )
                        # 标记跳过后续步骤（在后续判断中会检查这个条件）
                        # 注意：这里不直接return，而是通过后续的判断逻辑来跳过步骤
                else:
                    # 如果没有相关文档，设为 None
                    knowledge_refs = None
                    knowledge_confidence = 0.0
                    logger.warning(
                        f"[诊断流程][第四步] ⚠️ 所有知识库文档评估为不相关，置信分=0.0%，"
                        f"将继续执行后续步骤（第五步到第八步）"
                    )
                    action_results.append({"name": "step4_evaluate_knowledge", "status": "not_relevant", "details": {}})
            elif knowledge_refs:
                # 有知识库但LLM未启用，默认低置信度
                knowledge_confidence = 0.3
                action_results.append({"name": "step4_evaluate_knowledge", "status": "skipped", "details": {"reason": "LLM未启用"}})
            else:
                # 第三步未搜索到知识库
                knowledge_confidence = 0.0
                action_results.append({"name": "step4_evaluate_knowledge", "status": "skipped", "details": {"reason": "未搜索到知识库"}})
        else:
            # 第一步置信分 >= 0.8，跳过此步骤
            action_results.append({"name": "step4_evaluate_knowledge", "status": "skipped", "details": {"reason": "第一步置信分已达到阈值"}})
        
        # ========== 第五步到第八步：根据置信分决定后续流程 ==========
        # confidence_threshold 已在函数开始处定义
        external_refs: Optional[List[Dict[str, Any]]] = None
        llm_result: Optional[Dict[str, Any]] = None
        llm_confidence: float = 0.0  # 第六步的模型分析置信分
        llm_confidence_step8: float = 0.0  # 第八步的模型分析置信分（基于外部搜索）
        k8s_resources = None  # 扩展的K8s资源信息
        enhanced_problem_summary = ""  # 扩展信息增强的问题描述
        
        # 如果第一步置信分 >= 0.8 或 第四步知识库置信分 >= 0.8，直接完成诊断，跳过后续步骤
        if llm_confidence_step1 >= confidence_threshold:
            # 第一步已完成诊断，已在上面的逻辑中处理
            pass
        elif knowledge_confidence >= confidence_threshold:
            logger.info(
                f"[诊断流程] 第四步：知识库置信分{knowledge_confidence:.2%}>=阈值{confidence_threshold:.2%}，"
                f"直接完成诊断，跳过第五步到第八步"
            )
            # 注意：不设置llm_confidence，因为应该使用知识库置信分作为最终置信分
            # 跳过第五步到第八步
            action_results.append({"name": "step5_expand_k8s_resources", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
            action_results.append({"name": "step6_llm_analysis_with_k8s", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
            action_results.append({"name": "step7_search_external", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
            action_results.append({"name": "step8_llm_final_with_external", "status": "skipped", "details": {"reason": "第四步知识库置信分已达到阈值"}})
        else:
            # 第一步置信分 < 0.8 AND (第三步未搜索到知识库 OR 第四步知识库置信分 < 0.8)，继续执行第五步到第八步
            
            # ========== 第五步：扩展 K8s 信息收集（第一层扩展，条件触发）==========
            # **触发条件**：
            #   - 第一步的模型分析置信分 < 0.8 **AND**
            #   - (第三步未搜索到知识库 **OR** 第四步知识库置信分 < 0.8)
            # **跳过条件**：
            #   - 如果第一步置信分 >= 0.8，跳过此步骤（已在上面处理）
            #   - 如果第四步知识库置信分 >= 0.8，跳过此步骤（已在上面处理）
            if llm_confidence_step1 < confidence_threshold and knowledge_confidence < confidence_threshold:
                await self.record_service.append_event(
                    record.id,
                    self._make_event("step5_expand_k8s_resources", f"[迭代 {iteration_no}] 开始扩展K8s信息收集", "info"),
                )
                
                # 检查是否已经收集过相关资源
                k8s_resources_collected = await self.k8s_collector.check_k8s_resources_collected(record.id)
                if not k8s_resources_collected:
                    await self.k8s_collector.collect_related_k8s_resources(
                        record, cluster, runtime, context, iteration, self._make_event
                    )
                    # 获取收集到的K8s资源信息
                    memories = await self.memory_service.list_by_diagnosis(record.id)
                    for memory in memories:
                        if memory.memory_type == "k8s_resource":
                            k8s_resources = memory.content
                            break
                    action_results.append({"name": "step5_expand_k8s_resources", "status": "success", "details": {"collected": bool(k8s_resources)}})
                else:
                    # 已收集过，直接获取
                    memories = await self.memory_service.list_by_diagnosis(record.id)
                    for memory in memories:
                        if memory.memory_type == "k8s_resource":
                            k8s_resources = memory.content
                            break
                    action_results.append({"name": "step5_expand_k8s_resources", "status": "already_collected", "details": {"collected": bool(k8s_resources)}})
                
                # 保存到记忆
                if k8s_resources:
                    await self.memory_service.add_memory(
                        record.id,
                        memory_type="k8s_resource",
                        summary=f"[迭代 {iteration_no}] 第五步：扩展K8s信息收集完成",
                        content=k8s_resources,
                        iteration_id=iteration.id,
                        iteration_no=iteration_no,
                    )
            else:
                # 第一步置信分 >= 0.8 或 第四步知识库置信分 >= 0.8，跳过第五步
                action_results.append({"name": "step5_expand_k8s_resources", "status": "skipped", "details": {"reason": "第一步或第四步置信分已达到阈值"}})
            
            # ========== 第六步：基于扩展 K8s 信息的模型分析（条件触发）==========
            # **触发条件**：已完成第五步扩展K8s信息收集
            # **跳过条件**：
            #   - 如果第一步置信分 >= 0.8，跳过此步骤
            #   - 如果第四步知识库置信分 >= 0.8，跳过此步骤
            if llm_confidence_step1 < confidence_threshold and knowledge_confidence < confidence_threshold:
                if settings.OLLAMA_MODEL:
                    await self.record_service.append_event(
                        record.id,
                        self._make_event(
                            "step6_llm_analysis_with_k8s",
                            f"[迭代 {iteration_no}] 开始基于扩展K8s信息的模型分析（知识库置信分{knowledge_confidence:.2%}<阈值）",
                            "info",
                        ),
                    )
                    prior_memories_step6 = await self._get_prior_memories_for_llm(record.id, iteration_no)
                    
                    # 基于扩展K8s资源信息，调用LLM分析问题和答案
                    # 不传入知识库内容（因为知识库置信分<0.8，已不可信）
                    llm_result_step6 = await self.llm_service.call_llm(
                        context, metrics_data, logs_data, rule_findings, None, None,  # knowledge_refs=None, external_refs=None
                        k8s_resources, None, prior_memories_step6, api_data, change_events, resource_type  # deep_context=None
                    )
                    
                    # 提取置信度
                    if isinstance(llm_result_step6, dict) and "confidence" in llm_result_step6:
                        llm_confidence = float(llm_result_step6.get("confidence", 0.0))
                    else:
                        llm_confidence = 0.3
                    
                    logger.info(
                        f"[诊断流程][第六步] 基于扩展K8s信息的模型分析完成: 置信分={llm_confidence:.2%}, "
                        f"阈值={confidence_threshold:.2%}, 知识库置信分={knowledge_confidence:.2%}"
                    )
                    
                    await self.record_service.append_event(
                        record.id,
                        self._make_event(
                            "step6_llm_analysis_with_k8s",
                            f"[迭代 {iteration_no}] 基于扩展K8s信息的模型分析完成（置信度: {llm_confidence:.2%}）",
                            "success" if llm_result_step6 else "info",
                        ),
                    )
                    action_results.append(
                        {
                            "name": "step6_llm_analysis_with_k8s",
                            "status": "success" if llm_result_step6 else "empty",
                            "details": {"confidence": llm_confidence},
                        }
                    )
                    # 保存到记忆（符合设计文档要求：第六步保存到记忆 memory_type: llm）
                    if llm_result_step6:
                        await self.memory_service.add_memory(
                            record.id,
                            memory_type="llm",
                            summary=f"[迭代 {iteration_no}] 第六步：基于扩展K8s信息的模型分析完成（置信度: {llm_confidence:.2%}）",
                            content=llm_result_step6,
                            iteration_id=iteration.id,
                            iteration_no=iteration_no,
                        )
                        llm_result = llm_result_step6
                    
                    # 如果置信分 >= 0.8，完成诊断，跳过后续步骤
                    if llm_confidence >= confidence_threshold:
                        logger.info(
                            f"[诊断流程][第六步] ✅ 模型分析置信分{llm_confidence:.2%}>=阈值{confidence_threshold:.2%}，"
                            f"完成诊断，跳过后续步骤（第七步和第八步）"
                        )
                        action_results.append({"name": "step7_search_external", "status": "skipped", "details": {"reason": "第六步置信分已达到阈值"}})
                        action_results.append({"name": "step8_llm_final_with_external", "status": "skipped", "details": {"reason": "第六步置信分已达到阈值"}})
                    else:
                        logger.info(
                            f"[诊断流程][第六步] ⚠️ 模型分析置信分{llm_confidence:.2%}<阈值{confidence_threshold:.2%}，"
                            f"将继续执行后续步骤（第七步和第八步）"
                        )
                else:
                    # LLM未启用，跳过第六步
                    action_results.append({"name": "step6_llm_analysis_with_k8s", "status": "skipped", "details": {"reason": "LLM未启用"}})
            else:
                # 第一步置信分 >= 0.8 或 第四步知识库置信分 >= 0.8，跳过此步骤
                action_results.append({"name": "step6_llm_analysis_with_k8s", "status": "skipped", "details": {"reason": "第一步或第四步置信分已达到阈值"}})
            
            # ========== 第七步：外部搜索（条件触发）==========
            # **触发条件**：
            #   - 第一步的模型分析置信分 < 0.8 **AND**
            #   - (第四步未执行或知识库置信分 < 0.8) **AND**
            #   - (第六步未执行或第六步置信分 < 0.8)
            # **跳过条件**：
            #   - 如果第一步置信分 >= 0.8，跳过此步骤（已在上面处理）
            #   - 如果第四步知识库置信分 >= 0.8，跳过此步骤（已在上面处理）
            #   - 如果第六步置信分 >= 0.8，跳过此步骤
            # 注意：这里已经处于 else 分支，说明第一步置信分 < 0.8 且 第四步知识库置信分 < 0.8
            if llm_confidence < confidence_threshold:
                # ========== 第七步：外部搜索（条件触发）==========
                logger.info(
                    f"[诊断流程][第七步] 开始外部搜索: 第一步置信分={llm_confidence_step1:.2%}, "
                    f"第四步知识库置信分={knowledge_confidence:.2%}, 第六步置信分={llm_confidence:.2%}<阈值={confidence_threshold:.2%}"
                )
                await self.record_service.append_event(
                    record.id,
                    self._make_event(
                        "step7_search_external",
                        f"[迭代 {iteration_no}] 置信度不足，开始外部搜索",
                        "info",
                    ),
                )
                # 使用第二步生成的问题总结作为搜索关键词（符合设计文档要求）
                search_query = problem_summary if problem_summary else f"{resource_type} {resource_name} 在命名空间 {namespace} 出现问题"
                logger.info(f"[诊断流程][第七步] 外部搜索查询: {search_query[:100]}...")
                external_refs = await self.data_collector.search_external(search_query, resource_name, namespace)
                logger.info(
                    f"[诊断流程][第七步] 外部搜索完成: {'找到' if external_refs else '未找到'}结果 "
                    f"(结果数: {len(external_refs) if external_refs else 0})"
                )
                await self.record_service.append_event(
                    record.id,
                    self._make_event(
                        "step7_search_external",
                        f"[迭代 {iteration_no}] 外部搜索{'命中' if external_refs else '未命中'}", 
                        "success" if external_refs else "info",
                    ),
                )
                action_results.append(
                    {
                        "name": "step7_search_external",
                        "status": "found" if external_refs else "not_found",
                        "details": {
                            "count": len(external_refs) if external_refs else 0,
                            "trigger_reason": f"第一步置信分{llm_confidence_step1:.2%}、第四步知识库置信分{knowledge_confidence:.2%}、第六步置信分{llm_confidence:.2%}都低于阈值{confidence_threshold:.2%}",
                        },
                    }
                )
                
                if external_refs:
                    await self.memory_service.add_memory(
                        record.id,
                        memory_type="search",
                        summary=f"[迭代 {iteration_no}] 第七步：外部搜索获得 {len(external_refs)} 条参考",
                        content=external_refs,
                        iteration_id=iteration.id,
                        iteration_no=iteration_no,
                    )
                    
                    # ========== 第八步：基于外部搜索结果的模型分析（条件触发）==========
                    # **触发条件**：第七步进行了外部搜索
                    # **跳过条件**：如果第七步未执行，跳过此步骤
                    if settings.OLLAMA_MODEL:
                        await self.record_service.append_event(
                            record.id,
                            self._make_event("step8_llm_final_with_external", f"[迭代 {iteration_no}] 开始基于外部搜索结果的模型分析", "info"),
                        )
                        prior_memories_step8 = await self._get_prior_memories_for_llm(record.id, iteration_no)
                        # 传入收集的数据（指标、日志、规则检测结果、API数据）、扩展的 K8s 资源信息、外部搜索结果
                        # 不传入知识库内容（因为知识库置信分<0.8，已不可信）
                        llm_result_step8 = await self.llm_service.call_llm(
                            context, metrics_data, logs_data, rule_findings, None, external_refs,  # knowledge_refs=None
                            k8s_resources, None, prior_memories_step8, api_data, change_events, resource_type  # deep_context=None
                        )
                        # 更新置信度（第八步的模型分析置信分）
                        if isinstance(llm_result_step8, dict) and "confidence" in llm_result_step8:
                            llm_confidence_step8 = float(llm_result_step8.get("confidence", 0.0))
                        else:
                            llm_confidence_step8 = 0.3
                        
                        logger.info(
                            f"[诊断流程][第八步] 基于外部搜索结果的模型分析完成: 置信分={llm_confidence_step8:.2%}, "
                            f"阈值={confidence_threshold:.2%}, 外部搜索结果数={len(external_refs) if external_refs else 0}, "
                            f"第一步置信分={llm_confidence_step1:.2%}, 第四步知识库置信分={knowledge_confidence:.2%}, "
                            f"第六步置信分={llm_confidence:.2%}"
                        )
                        
                        await self.record_service.append_event(
                            record.id,
                            self._make_event(
                                "step8_llm_final_with_external",
                                f"[迭代 {iteration_no}] 基于外部搜索结果的模型分析完成（置信度: {llm_confidence_step8:.2%}）",
                                "success" if llm_result_step8 else "info",
                            ),
                        )
                        action_results.append(
                            {
                                "name": "step8_llm_final_with_external",
                                "status": "success" if llm_result_step8 else "empty",
                                "details": {"confidence": llm_confidence_step8},
                            }
                        )
                        # 保存到记忆（符合设计文档要求：第八步保存到记忆 memory_type: llm）
                        if llm_result_step8:
                            await self.memory_service.add_memory(
                                record.id,
                                memory_type="llm",
                                summary=f"[迭代 {iteration_no}] 第八步：基于外部搜索结果的模型分析完成（置信度: {llm_confidence_step8:.2%}）",
                                content=llm_result_step8,
                                iteration_id=iteration.id,
                                iteration_no=iteration_no,
                            )
                            llm_result = llm_result_step8
                    else:
                        action_results.append({"name": "step8_llm_final_with_external", "status": "skipped", "details": {"reason": "LLM未启用"}})
                else:
                    # 第七步未进行外部搜索，跳过第八步
                    action_results.append({"name": "step8_llm_final_with_external", "status": "skipped", "details": {"reason": "第七步未进行外部搜索"}})
            else:
                # 第六步置信分 >= 0.8，跳过第七步和第八步
                # 注意：如果第六步置信分 >= 0.8，第六步内部已经标记跳过了第七步和第八步（第876-877行）
                # 这里再次标记是为了确保完整性（如果第六步未执行但llm_confidence >= threshold的情况）
                action_results.append({"name": "step7_search_external", "status": "skipped", "details": {"reason": "第六步置信分已达到阈值"}})
                action_results.append({"name": "step8_llm_final_with_external", "status": "skipped", "details": {"reason": "第六步置信分已达到阈值"}})
        
        # 如果第一步完成了诊断（置信分 >= 0.8），使用第一步的结果
        if llm_confidence_step1 >= confidence_threshold and llm_result_step1:
            llm_result = llm_result_step1
        
        # 注意：llm_result 已在第一步、第六步或第八步中分别保存到记忆（符合设计文档要求）

        # 从结构化 LLM 输出中提取信息，或使用传统方法生成摘要
        summary, conclusion, computed_confidence, root_cause, timeline, impact_scope, structured_solutions = self.summary_service.generate_summary_enhanced(
            metrics_data, logs_data, knowledge_refs, rule_findings, llm_result, context
        )
        
        # 确定最终置信分（按执行顺序，取第一个 >= 0.8 的置信分，严格符合设计文档要求）：
        # 1. **基于实际数据的模型分析置信分（第一步）** ⭐【最高优先级】
        #    如果日志中有明确的错误信息，模型应该能够直接识别并给出高置信分
        #    这是最直接、最可靠的证据，优先使用
        # 2. 知识库评估置信分（第四步，如果知识库命中且置信分 >= 0.8）
        # 3. 扩展K8s信息的模型分析置信分（第六步，如果基于扩展资源分析后置信分 >= 0.8）
        # 4. 外部搜索后的模型分析置信分（第八步，如果基于外部搜索结果分析后置信分 >= 0.8）
        # 5. 否则，使用最后一次模型调用的置信分
        logger.info(
            f"[诊断流程][最终置信分确定] 开始确定最终置信分，候选值: "
            f"第一步模型分析置信分={llm_confidence_step1:.2%}, "
            f"第四步知识库置信分={knowledge_confidence:.2%}, "
            f"第六步模型分析置信分={llm_confidence:.2%}, "
            f"第八步模型分析置信分={llm_confidence_step8:.2%}, "
            f"计算置信分={computed_confidence:.2%}, "
            f"阈值={confidence_threshold:.2%}"
        )
        confidence = 0.0
        if llm_confidence_step1 >= confidence_threshold:
            # 优先级1：基于实际数据的模型分析置信分（第一步）⭐【最高优先级】
            confidence = llm_confidence_step1
            logger.info(
                f"[诊断流程][最终置信分确定] ✅ 优先级1: 使用第一步模型分析置信分={confidence:.2%} "
                f"（基于实际数据，置信分>=阈值）⭐【最高优先级】"
            )
        elif knowledge_refs and knowledge_confidence >= confidence_threshold:
            # 优先级2：知识库评估置信分（第四步，如果知识库命中且置信分>=0.8）
            confidence = knowledge_confidence
            logger.info(
                f"[诊断流程][最终置信分确定] ✅ 优先级2: 使用知识库置信分={confidence:.2%} "
                f"（来自第四步，知识库命中，置信分>=阈值）"
            )
        elif llm_confidence >= confidence_threshold:
            # 优先级3：扩展K8s信息的模型分析置信分（第六步，如果基于扩展资源分析后置信分>=0.8）
            confidence = llm_confidence
            logger.info(
                f"[诊断流程][最终置信分确定] ✅ 优先级3: 使用第六步模型分析置信分={confidence:.2%} "
                f"（基于扩展K8s信息，置信分>=阈值）"
            )
        elif llm_confidence_step8 > 0:
            # 优先级4：基于外部搜索结果的模型分析置信分（第八步，如果进行了外部搜索）
            # 注意：如果进行了外部搜索，使用第八步的置信分（无论是否>=阈值，符合设计文档要求）
            confidence = llm_confidence_step8
            logger.info(
                f"[诊断流程][最终置信分确定] ✅ 优先级4: 使用第八步模型分析置信分={confidence:.2%} "
                f"（基于外部搜索，无论是否>=阈值）"
            )
        elif llm_confidence_step1 > 0:
            # 优先级5：第一步的模型分析置信分（如果置信分<0.8，但至少执行了第一步）
            confidence = llm_confidence_step1
            logger.info(
                f"[诊断流程][最终置信分确定] ✅ 优先级5: 使用第一步模型分析置信分={confidence:.2%} "
                f"（基于实际数据，置信分<阈值）"
            )
        elif llm_confidence > 0:
            # 优先级6：第六步的模型分析置信分（如果置信分<0.8）
            confidence = llm_confidence
            logger.info(
                f"[诊断流程][最终置信分确定] ✅ 优先级6: 使用第六步模型分析置信分={confidence:.2%} "
                f"（基于扩展K8s信息，置信分<阈值）"
            )
        else:
            # 优先级7：使用计算出的置信度
            confidence = computed_confidence
            logger.info(
                f"[诊断流程][最终置信分确定] ✅ 优先级7: 使用计算的置信度={confidence:.2%} "
                f"（fallback策略）"
            )
        
        knowledge_source = self.summary_service.determine_knowledge_source(
            knowledge_refs,
            knowledge_confidence,
            llm_result,
            rule_findings,
        )

        await self.memory_service.add_memory(
            record.id,
            memory_type="conclusion",
            summary=f"[迭代 {iteration_no}] {conclusion}",
            content={
                "summary": summary,
                "conclusion": conclusion,
                "confidence": confidence,
                "knowledge_source": knowledge_source,
            },
            iteration_id=iteration.id,
            iteration_no=iteration_no,
        )

        reasoning_output = {
            "rule_findings": rule_findings,
            "knowledge_refs": knowledge_refs,
            "external_refs": external_refs,
            "llm_result": llm_result,
        }
        # 如果 LLM 返回结构化结果，添加根因分析信息
        if isinstance(llm_result, dict):
            if "root_cause_analysis" in llm_result:
                reasoning_output["root_cause_analysis"] = llm_result.get("root_cause_analysis")
            if "evidence_chain" in llm_result:
                reasoning_output["evidence_chain"] = llm_result.get("evidence_chain")
        
        iteration_metadata = {
            "context": context,
            "trigger_source": trigger_source,
            "trigger_payload": trigger_payload,
        }
        await self.iteration_service.complete_iteration(
            iteration.id,
            reasoning_summary=conclusion,
            reasoning_output=reasoning_output,
            action_plan=action_plan,
            action_result=action_results,
            metadata=iteration_metadata,
        )

        await self.record_service.append_event(
            record.id,
            self._make_event("iteration", f"迭代 {iteration_no} 完成，生成结论", "success"),
        )

        return {
            "summary": summary,
            "conclusion": conclusion,
            "confidence": confidence,
            "knowledge_source": knowledge_source,
            "knowledge_refs": knowledge_refs,
            "external_refs": external_refs,
            "llm_result": llm_result,
            "root_cause": root_cause,
            "timeline": timeline,
            "impact_scope": impact_scope,
            "solutions": structured_solutions,
            "metrics": metrics_data,
            "logs": logs_data,
            "rule_findings": rule_findings,
            "action_plan": action_plan,
            "action_results": action_results,
        }

    def _apply_iteration_result(self, record: Any, iteration: Any, iteration_result: Dict[str, Any]) -> None:
        iteration_key = f"iteration_{iteration.iteration_no}"

        metrics = record.metrics or {}
        metrics[iteration_key] = iteration_result.get("metrics")
        record.metrics = metrics

        logs = record.logs or {}
        logs[iteration_key] = iteration_result.get("logs")
        record.logs = logs

        # 增强的 recommendations：包含结构化解决方案
        recommendations = record.recommendations or {}
        iterations_map = recommendations.setdefault("iterations", {})
        iterations_map[iteration_key] = {
            "knowledge_refs": iteration_result.get("knowledge_refs"),
            "rule_findings": iteration_result.get("rule_findings"),
            "external_refs": iteration_result.get("external_refs"),
            "llm_result": iteration_result.get("llm_result"),
        }
        
        # 如果有结构化解决方案，添加到 recommendations
        structured_solutions = iteration_result.get("solutions")
        if structured_solutions:
            recommendations["solutions"] = structured_solutions
            recommendations["latest"] = {
                **iterations_map[iteration_key],
                "solutions": structured_solutions,
            }
        else:
            recommendations["latest"] = iterations_map[iteration_key]
        
        record.recommendations = recommendations

        # 处理 knowledge_refs：schema 要求是 List[int]（document_id 列表），需要从文档对象列表提取
        knowledge_refs_raw = iteration_result.get("knowledge_refs")
        if knowledge_refs_raw and isinstance(knowledge_refs_raw, list):
            if not knowledge_refs_raw:
                # 空列表
                record.knowledge_refs = None
            elif isinstance(knowledge_refs_raw[0], dict):
                # 文档对象列表，提取 document_id
                knowledge_refs_ids = [
                    int(doc.get("document_id"))
                    for doc in knowledge_refs_raw
                    if doc.get("document_id") is not None
                ]
                record.knowledge_refs = knowledge_refs_ids if knowledge_refs_ids else None
            elif isinstance(knowledge_refs_raw[0], int):
                # 已经是整数列表，直接使用
                record.knowledge_refs = knowledge_refs_raw
            else:
                record.knowledge_refs = None
        else:
            record.knowledge_refs = None
        
        record.knowledge_source = iteration_result.get("knowledge_source")
        record.summary = iteration_result.get("summary")
        record.conclusion = iteration_result.get("conclusion")
        record.confidence = iteration_result.get("confidence")
        
        # 新增字段：保存到 symptoms JSON 中（因为数据库模型已有 symptoms 字段）
        # 注意：必须保留已有的 symptoms 数据（如 config），只更新新字段
        # 使用深拷贝确保不会丢失已有数据
        import copy
        symptoms = copy.deepcopy(record.symptoms) if record.symptoms and isinstance(record.symptoms, dict) else {}
        
        # 确保保留已有的 config 字段（如果存在）
        existing_config = symptoms.get("config")
        existing_keys_before = list(symptoms.keys()) if isinstance(symptoms, dict) else []
        
        logger.warning(
            f"[诊断流程] _apply_iteration_result 开始更新 symptoms: "
            f"现有键={existing_keys_before}, 是否有 config={bool(existing_config)}, "
            f"config 类型={type(existing_config).__name__ if existing_config else None}, "
            f"config 键数量={len(existing_config) if isinstance(existing_config, dict) else 0}"
        )
        
        if iteration_result.get("root_cause"):
            symptoms["root_cause"] = iteration_result.get("root_cause")
        if iteration_result.get("timeline"):
            symptoms["timeline"] = iteration_result.get("timeline")
        if iteration_result.get("impact_scope"):
            symptoms["impact_scope"] = iteration_result.get("impact_scope")
        if iteration_result.get("llm_result") and isinstance(iteration_result.get("llm_result"), dict):
            llm_result = iteration_result.get("llm_result")
            if "root_cause_analysis" in llm_result:
                symptoms["root_cause_analysis"] = llm_result.get("root_cause_analysis")
            if "evidence_chain" in llm_result:
                symptoms["evidence_chain"] = llm_result.get("evidence_chain")
        
        # 确保 config 字段被保留（如果之前存在，或者现在存在但被覆盖了）
        if existing_config:
            symptoms["config"] = existing_config
            logger.warning(
                f"[诊断流程] 在 _apply_iteration_result 中保留 config 字段: "
                f"键数量={len(existing_config) if isinstance(existing_config, dict) else 0}, "
                f"最终 symptoms 键={list(symptoms.keys())[:15]}"
            )
        else:
            # 即使 existing_config 为空，也检查 record.symptoms 是否还有 config
            if isinstance(record.symptoms, dict) and record.symptoms.get("config"):
                symptoms["config"] = record.symptoms.get("config")
                logger.warning(
                    f"[诊断流程] 在 _apply_iteration_result 中从 record.symptoms 恢复 config 字段: "
                    f"键数量={len(symptoms.get('config', {})) if isinstance(symptoms.get('config'), dict) else 0}"
                )
        
        record.symptoms = symptoms
        
        # 最终验证
        final_symptoms_keys = list(record.symptoms.keys()) if isinstance(record.symptoms, dict) else []
        final_has_config = isinstance(record.symptoms, dict) and "config" in record.symptoms
        logger.warning(
            f"[诊断流程] _apply_iteration_result 完成: "
            f"最终 symptoms 键={final_symptoms_keys}, 是否有 config={final_has_config}"
        )

    def _find_iteration_by_no(self, record: Any, iteration_no: int) -> Optional[Any]:
        if not record or not record.iterations:
            return None
        for iteration in record.iterations:
            if iteration.iteration_no == iteration_no:
                return iteration
        return None

    @staticmethod
    def _extract_highest_completed_step(action_results: Optional[List[Dict[str, Any]]]) -> int:
        if not action_results:
            return 0
        highest = 0
        for result in action_results:
            if not isinstance(result, dict):
                continue
            name = result.get("name") or ""
            if not name.startswith("step"):
                continue
            try:
                step_no = int("".join(ch for ch in name if ch.isdigit()) or 0)
            except ValueError:
                step_no = 0
            if step_no <= 0:
                continue
            status = (result.get("status") or "").lower()
            if status != "skipped":
                highest = max(highest, step_no)
        return highest

    async def _handle_feedback_confirmed(self, record: Any) -> None:
        cluster = await self.cluster_service.get(record.cluster_id)
        if not cluster:
            logger.warning("确认反馈失败：集群 %s 不存在", record.cluster_id)
            return
        symptoms = record.symptoms or {}
        if symptoms.get("knowledge_sedimented"):
            return
        try:
            await self.report_service.save_diagnosis_to_knowledge_base(record, cluster)
            await self.record_service.append_event(
                record.id,
                self._make_event("feedback", "用户确认结论，已沉淀到知识库", "success"),
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("根据反馈进行知识沉淀失败: %s", exc)

    async def _handle_feedback_continue(
        self,
        record: Any,
        continue_from_step: int,
        min_steps_before_exit: int,
        notes: Optional[str] = None,
    ) -> None:
        await self.record_service.append_event(
            record.id,
            self._make_event(
                "feedback",
                f"根据反馈继续排查（此前执行到第 {continue_from_step} 步）: {notes or '无备注'}",
                "warning",
            ),
        )
        record.status = "running"
        record.completed_at = None
        record.confidence = 0.5
        self.record_service.db.commit()
        self.record_service.db.refresh(record)

        cluster = await self.cluster_service.get(record.cluster_id)
        if not cluster:
            raise ValueError("无法继续诊断：关联集群不存在")

        runtime = self.cluster_service.build_runtime_payload(cluster)
        symptoms = record.symptoms or {}
        time_range_hours = symptoms.get("time_range_hours")
        if isinstance(time_range_hours, str):
            try:
                time_range_hours = float(time_range_hours)
            except ValueError:
                time_range_hours = None
        if not isinstance(time_range_hours, (int, float)):
            time_range_hours = 2.0

        context = {
            "cluster_id": record.cluster_id,
            "namespace": record.namespace,
            "resource_type": record.resource_type or "pods",
            "resource_name": record.resource_name,
            "time_range_hours": time_range_hours,
            "min_steps_before_exit": max(1, min_steps_before_exit),
            "feedback_continue_from_step": continue_from_step,
            "last_feedback_iteration": (record.feedback or {}).get("state", {}).get("last_feedback_iteration"),
        }

        await self._execute_iteration(
            record=record,
            cluster=cluster,
            runtime=runtime,
            context=context,
            trigger_source=record.trigger_source or "manual",
            trigger_payload=record.trigger_payload,
        )

    async def _execute_iteration(
        self,
        record: Any,
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
        context: Dict[str, Any],
        trigger_source: str,
        trigger_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prior_summaries = await self._get_recent_memory_summaries(record.id)
        prompt = self.summary_service.build_reasoning_prompt(cluster, context, trigger_payload, prior_summaries)
        iteration = await self.iteration_service.start_iteration(
            record.id,
            stage="initializing",
            reasoning_prompt=prompt,
            metadata={"context": context, "trigger_source": trigger_source},
        )
        iteration.stage = f"iteration_{iteration.iteration_no}"
        iteration.meta = (iteration.meta or {}) | {"iteration_index": iteration.iteration_no}
        self.iteration_service.db.commit()
        self.iteration_service.db.refresh(iteration)

        if iteration.iteration_no == 1:
            await self.memory_service.add_memory(
                record.id,
                memory_type="symptom",
                summary="初始症状",
                content={"context": context, "trigger_payload": trigger_payload},
                iteration_id=iteration.id,
                iteration_no=iteration.iteration_no,
            )

        try:
            iteration_result = await self._run_single_iteration(
                record=record,
                cluster=cluster,
                runtime=runtime,
                context=context,
                iteration=iteration,
                trigger_source=trigger_source,
                trigger_payload=trigger_payload,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Diagnosis iteration failed: %s\n%s", exc, traceback.format_exc())
            await self.record_service.append_event(
                record.id,
                self._make_event("error", f"迭代 {iteration.iteration_no} 失败: {exc}", "error"),
            )
            await self.record_service.update_status(record.id, "failed")
            await self.iteration_service.fail_iteration(
                iteration.id,
                str(exc),
                action_result=[],
            )
            await self.memory_service.add_memory(
                record.id,
                memory_type="error",
                summary=str(exc),
                content={"traceback": traceback.format_exc()},
                iteration_id=iteration.id,
                iteration_no=iteration.iteration_no,
            )
            raise

        self._apply_iteration_result(record, iteration, iteration_result)

        # ========== 判断终止条件（基于最终的置信分）==========
        # 根据设计文档：单轮迭代内已完成所有8个诊断步骤，不再进行多轮迭代
        # 注意：最终置信分已在 _run_single_iteration 中确定，这里直接使用
        confidence_threshold = max(0.0, min(1.0, settings.OBSERVABILITY_DIAGNOSIS_CONFIDENCE_THRESHOLD))
        final_confidence = iteration_result.get("confidence") or 0.0
        knowledge_source = iteration_result.get("knowledge_source")

        # 条件1: 经过这8个步骤后，置信分 >= 阈值 (0.8)
        if final_confidence >= confidence_threshold:
            record.status = "completed"
            record.completed_at = datetime.utcnow()
            await self.record_service.append_event(
                record.id,
                self._make_event("iteration", f"迭代 {iteration.iteration_no} 达到终止条件（置信分{final_confidence:.2%}>=阈值{confidence_threshold:.2%}）", "success"),
            )
            iteration_result["status"] = "completed"
            # 知识沉淀：诊断完成后自动提取并保存到知识库
            try:
                await self.report_service.save_diagnosis_to_knowledge_base(record, cluster)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("知识沉淀失败: %s", exc)
        else:
            # 条件2: 经过这8个步骤后，置信分 < 阈值 (0.8)
            # 生成诊断报告，申请人工介入
            # 说明：单轮迭代内已完成所有8个诊断步骤（模型分析、知识库搜索、扩展K8s信息、外部搜索等），
            #       但置信分仍不足，需要人工专家介入进行深度分析
            # 注意：不再进行下一轮迭代，因为单轮迭代内已尝试所有可能的诊断方法
            await self.report_service.generate_diagnosis_report(record, iteration_result, self.record_service, self._make_event)
            record.status = "pending_human"
            record.completed_at = None
            await self.record_service.append_event(
                record.id,
                self._make_event(
                    "iteration",
                    f"经过9个步骤后，置信分{final_confidence:.2%}<阈值{confidence_threshold:.2%}，已生成诊断报告，申请人工介入",
                    "warning",
                ),
            )
            iteration_result["status"] = "pending_human"

        self.record_service.db.commit()
        self.record_service.db.refresh(record)
        return iteration_result

    # K8s 资源收集、深度诊断、报告生成和知识沉淀相关方法已移至以下模块：
    # - diagnosis_k8s_collector.py: K8s 资源收集和深度诊断
    # - diagnosis_report_service.py: 报告生成和知识沉淀

    def _schedule_next_iteration(self, record_id: int) -> None:
        """调度下一轮诊断迭代"""
        if not settings.OBSERVABILITY_ENABLE_SCHEDULE:
            return
        try:
            delay = settings.OBSERVABILITY_DIAGNOSIS_ITERATION_DELAY_SECONDS
            celery_app.send_task(
                "app.tasks.observability.continue_diagnosis",
                args=[record_id],
                countdown=delay,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("调度下一轮诊断失败: %s", exc)

    async def _get_recent_memory_summaries(self, diagnosis_id: int) -> List[str]:
        memories = await self.memory_service.list_by_diagnosis(diagnosis_id)
        if not memories:
            return []
        limit = max(1, settings.OBSERVABILITY_DIAGNOSIS_MEMORY_RECENT_LIMIT)
        summaries = [m.summary for m in memories if getattr(m, "summary", None)]
        return summaries[-limit:]

    async def _get_prior_memories_for_llm(self, diagnosis_id: int, current_iteration_no: int) -> List[Dict[str, Any]]:
        """
        获取历史记忆，用于传递给 LLM
        
        Args:
            diagnosis_id: 诊断记录ID
            current_iteration_no: 当前迭代序号（只获取之前的记忆）
            
        Returns:
            历史记忆列表，每个记忆包含 memory_type, summary, content, iteration_no
        """
        memories = await self.memory_service.list_by_diagnosis(diagnosis_id)
        if not memories:
            return []
        
        # 只获取当前迭代之前的记忆
        prior_memories = [
            {
                "memory_type": m.memory_type,
                "summary": m.summary or "",
                "content": m.content or {},
                "iteration_no": m.iteration_no or 0,
            }
            for m in memories
            if m.iteration_no and m.iteration_no < current_iteration_no
        ]
        
        # 按迭代序号排序，限制数量
        prior_memories.sort(key=lambda x: x["iteration_no"])
        limit = max(1, settings.OBSERVABILITY_DIAGNOSIS_MEMORY_RECENT_LIMIT)
        return prior_memories[-limit:]

    @staticmethod
    def _extract_config_from_api_data(api_data: Dict[str, Any], resource_type: str) -> Dict[str, Any]:
        """
        从 api_data 中提取配置信息
        
        Args:
            api_data: 包含 spec, status, metadata 的字典
            resource_type: 资源类型（pods, nodes, deployments 等）
        
        Returns:
            提取的配置信息字典
        """
        if not api_data or not isinstance(api_data, dict):
            return {}
        
        config: Dict[str, Any] = {}
        spec = api_data.get("spec", {})
        metadata = api_data.get("metadata", {})
        status = api_data.get("status", {})
        
        # 对于 Pod，提取容器配置、环境变量、卷挂载等
        if resource_type == "pods":
            containers = spec.get("containers", [])
            if containers:
                # 提取所有容器的环境变量
                env_vars: Dict[str, str] = {}
                for container in containers:
                    container_env = container.get("env", [])
                    for env_item in container_env:
                        if isinstance(env_item, dict):
                            name = env_item.get("name", "")
                            value = env_item.get("value", "")
                            if name:
                                env_vars[name] = value
                    # 从 envFrom 中提取 ConfigMap/Secret 的环境变量
                    env_from = container.get("envFrom", [])
                    for env_from_item in env_from:
                        if isinstance(env_from_item, dict):
                            config_map_ref = env_from_item.get("configMapRef", {})
                            if config_map_ref:
                                name = config_map_ref.get("name", "")
                                if name:
                                    env_vars[f"CONFIGMAP_{name}"] = f"configMapRef: {name}"
                
                if env_vars:
                    config.update(env_vars)
                
                # 提取卷挂载信息
                volumes = spec.get("volumes", [])
                volume_mounts = []
                for volume in volumes:
                    if isinstance(volume, dict):
                        volume_name = volume.get("name", "")
                        config_map = volume.get("configMap", {})
                        secret = volume.get("secret", {})
                        persistent_volume_claim = volume.get("persistentVolumeClaim", {})
                        if config_map:
                            volume_mounts.append({
                                "name": volume_name,
                                "type": "configMap",
                                "source": config_map.get("name", ""),
                            })
                        elif secret:
                            volume_mounts.append({
                                "name": volume_name,
                                "type": "secret",
                                "source": secret.get("secretName", ""),
                            })
                        elif persistent_volume_claim:
                            volume_mounts.append({
                                "name": volume_name,
                                "type": "persistentVolumeClaim",
                                "source": persistent_volume_claim.get("claimName", ""),
                            })
                
                if volume_mounts:
                    config["volumes"] = volume_mounts
        
        # 对于 Deployment/StatefulSet，提取副本数、策略等
        elif resource_type in ["deployments", "statefulsets", "daemonsets"]:
            replicas = spec.get("replicas")
            if replicas is not None:
                config["replicas"] = replicas
            
            strategy = spec.get("strategy", {})
            if strategy:
                config["strategy"] = strategy
        
        # 添加通用的配置信息
        if metadata.get("labels"):
            config["labels"] = metadata.get("labels")
        if metadata.get("annotations"):
            # 只提取关键注解，避免数据过大
            important_annotations = [
                "deployment.kubernetes.io/revision",
                "kubernetes.io/change-cause",
            ]
            filtered_annotations = {
                k: v for k, v in metadata.get("annotations", {}).items()
                if k in important_annotations
            }
            if filtered_annotations:
                config["annotations"] = filtered_annotations
        
        return config

    @staticmethod
    def _make_event(stage: str, message: str, status: str) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage": stage,
            "status": status,
            "message": message,
        }
