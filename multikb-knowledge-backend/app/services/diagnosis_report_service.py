"""
Diagnosis report and knowledge base service.
负责生成诊断报告和知识沉淀
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.config.settings import settings
from app.core.logging import logger
from app.models.cluster_config import ClusterConfig
from app.services.opensearch_service import OpenSearchService


class DiagnosisReportService:
    """诊断报告和知识沉淀服务"""

    def __init__(self, memory_service, iteration_service, opensearch_service: OpenSearchService):
        self.memory_service = memory_service
        self.iteration_service = iteration_service
        self.opensearch_service = opensearch_service

    async def generate_diagnosis_report(
        self, record: Any, iteration_result: Dict[str, Any], record_service, make_event_func
    ) -> None:
        """
        生成诊断报告（当无法判断问题时）
        
        包含：
        - 问题摘要
        - 已收集的信息清单
        - 分析结果
        - 建议的人工排查方向
        - 下一步操作建议
        """
        # 收集所有记忆信息
        memories = await self.memory_service.list_by_diagnosis(record.id)
        iterations = await self.iteration_service.list_by_diagnosis(record.id)
        
        # 统计收集的信息
        collected_info = {
            "metrics": False,
            "logs": False,
            "k8s_resources": False,
            "deep_context": False,
            "events": False,
            "knowledge_base": False,
            "external_search": False,
        }
        
        for memory in memories:
            if memory.memory_type == "metric":
                collected_info["metrics"] = True
            elif memory.memory_type == "log":
                collected_info["logs"] = True
            elif memory.memory_type == "k8s_resource":
                collected_info["k8s_resources"] = True
            elif memory.memory_type == "deep_context":
                collected_info["deep_context"] = True
                if memory.content and memory.content.get("events"):
                    collected_info["events"] = True
            elif memory.memory_type == "knowledge":
                collected_info["knowledge_base"] = True
            elif memory.memory_type == "search":
                collected_info["external_search"] = True
        
        # 生成报告
        report = {
            "summary": {
                "problem": f"{record.resource_type}/{record.resource_name} 在 {record.namespace} 命名空间异常",
                "diagnosis_duration": f"{len(iterations)} 轮迭代",
                "final_confidence": iteration_result.get("confidence", 0.0),
                "status": "无法确定根因，需要人工介入",
            },
            "collected_information": collected_info,
            "analysis_results": {
                "excluded_causes": [
                    "已检查 Pod 指标、日志、配置",
                    "已检查相关 K8s 资源（Deployment、Service、ConfigMap 等）",
                    "已检查节点状态和资源配额",
                ],
                "suspicious_points": [],
                "hypotheses": [
                    "可能是应用代码层面的问题",
                    "可能是外部依赖服务的问题",
                    "可能是集群基础设施的问题",
                    "可能需要更长时间范围的监控数据",
                ],
            },
            "recommended_actions": {
                "immediate_checks": [
                    f"检查 Pod 详细状态: kubectl describe pod {record.resource_name} -n {record.namespace}",
                    f"查看 Pod 事件: kubectl get events -n {record.namespace} --field-selector involvedObject.name={record.resource_name}",
                    f"检查 Deployment 状态: kubectl describe deployment -n {record.namespace}",
                    "检查应用日志中的错误模式",
                    "检查是否有最近的配置变更",
                ],
                "further_investigation": [
                    "对比同一 Deployment 下其他 Pod 的状态",
                    "检查节点资源使用情况",
                    "检查网络连接和 DNS 解析",
                    "检查存储卷状态",
                    "联系应用开发团队确认是否有代码变更",
                ],
                "monitoring_suggestions": [
                    "增加更长时间范围的指标监控",
                    "设置更详细的告警规则",
                    "记录问题发生时的完整上下文",
                ],
            },
            "next_steps": {
                "if_problem_persists": [
                    "收集完整的 Pod 和节点日志",
                    "执行 kubectl describe 和 kubectl get -o yaml 获取完整配置",
                    "联系 Kubernetes 集群管理员检查集群状态",
                    "联系应用团队进行代码审查",
                ],
                "if_problem_resolved": [
                    "分析问题恢复的原因",
                    "更新知识库，记录此次诊断经验",
                    "设置预防性监控",
                ],
            },
        }
        
        # 更新诊断记录的建议字段
        recommendations = record.recommendations or {}
        recommendations["diagnosis_report"] = report
        record.recommendations = recommendations
        
        await record_service.append_event(
            record.id,
            make_event_func(
                "report",
                "已生成详细诊断报告，包含所有收集的信息和建议的排查方向",
                "info",
            ),
        )

    async def save_diagnosis_to_knowledge_base(self, record: Any, cluster: ClusterConfig) -> None:
        """
        知识沉淀：将诊断结果自动提取并保存到知识库
        
        根据设计文档要求：
        - 诊断模块产出的报告通过现有知识库接口入库，结构化存储事件信息与结论
        - 以 cluster、namespace、service、alertname、指标模式 等字段建索引
        - 知识条目关联 Prometheus 标签、日志查询语句，便于快速跳转
        """
        try:
            # 1. 提取诊断信息
            symptoms = record.symptoms or {}
            recommendations = record.recommendations or {}
            llm_result = recommendations.get("latest", {}).get("llm_result") or {}
            
            # 2. 生成 Markdown 格式的诊断案例文档
            content_parts = []
            content_parts.append(f"# 诊断案例：{record.resource_type}/{record.resource_name}")
            content_parts.append("")
            content_parts.append(f"**集群**: {cluster.name}")
            content_parts.append(f"**命名空间**: {record.namespace or 'default'}")
            content_parts.append(f"**资源类型**: {record.resource_type}")
            content_parts.append(f"**资源名称**: {record.resource_name}")
            content_parts.append(f"**诊断时间**: {record.started_at.isoformat() if record.started_at else 'N/A'}")
            content_parts.append(f"**置信度**: {record.confidence or 0.0:.2%}")
            content_parts.append("")
            
            # 问题描述
            if record.summary:
                content_parts.append("## 问题描述")
                content_parts.append(record.summary)
                content_parts.append("")
            
            # 根因分析
            root_cause = symptoms.get("root_cause") or llm_result.get("root_cause")
            if root_cause:
                content_parts.append("## 根因分析")
                content_parts.append(root_cause)
                content_parts.append("")
            
            # 5 Why 分析
            root_cause_analysis = symptoms.get("root_cause_analysis") or llm_result.get("root_cause_analysis")
            if root_cause_analysis:
                content_parts.append("## 5 Why 分析")
                for i in range(1, 6):
                    why_key = f"why{i}"
                    if why_key in root_cause_analysis:
                        content_parts.append(f"{i}. {root_cause_analysis[why_key]}")
                content_parts.append("")
            
            # 证据链
            evidence_chain = symptoms.get("evidence_chain") or llm_result.get("evidence_chain")
            if evidence_chain:
                content_parts.append("## 证据链")
                for key, value in evidence_chain.items():
                    content_parts.append(f"- **{key}**: {value}")
                content_parts.append("")
            
            # 时间线
            timeline = symptoms.get("timeline") or llm_result.get("timeline")
            if timeline:
                content_parts.append("## 时间线")
                if timeline.get("problem_start"):
                    content_parts.append(f"- **问题开始**: {timeline['problem_start']}")
                if timeline.get("problem_escalate"):
                    content_parts.append(f"- **问题恶化**: {timeline['problem_escalate']}")
                if timeline.get("key_events"):
                    content_parts.append("- **关键事件**:")
                    for event in timeline["key_events"]:
                        content_parts.append(f"  - {event}")
                content_parts.append("")
            
            # 影响范围
            impact_scope = symptoms.get("impact_scope") or llm_result.get("impact_scope")
            if impact_scope:
                content_parts.append("## 影响范围")
                if impact_scope.get("affected_pods"):
                    content_parts.append(f"- **受影响的 Pod**: {', '.join(impact_scope['affected_pods'])}")
                if impact_scope.get("affected_services"):
                    content_parts.append(f"- **受影响的服务**: {', '.join(impact_scope['affected_services'])}")
                if impact_scope.get("affected_nodes"):
                    content_parts.append(f"- **受影响的节点**: {', '.join(impact_scope['affected_nodes'])}")
                if impact_scope.get("business_impact"):
                    content_parts.append(f"- **业务影响**: {impact_scope['business_impact']}")
                content_parts.append("")
            
            # 解决方案
            solutions = recommendations.get("solutions") or llm_result.get("solutions")
            if solutions:
                content_parts.append("## 解决方案")
                if solutions.get("immediate"):
                    content_parts.append("### 立即缓解措施")
                    for solution in solutions["immediate"]:
                        content_parts.append(f"- **{solution.get('title', 'N/A')}** (优先级: {solution.get('priority', 'N/A')})")
                        if solution.get("steps"):
                            for step in solution["steps"]:
                                content_parts.append(f"  - {step.get('action', 'N/A')}")
                    content_parts.append("")
                if solutions.get("root"):
                    content_parts.append("### 根本解决方案")
                    for solution in solutions["root"]:
                        content_parts.append(f"- **{solution.get('title', 'N/A')}** (优先级: {solution.get('priority', 'N/A')})")
                        if solution.get("steps"):
                            for step in solution["steps"]:
                                content_parts.append(f"  - {step.get('action', 'N/A')}")
                    content_parts.append("")
                if solutions.get("preventive"):
                    content_parts.append("### 预防措施")
                    for measure in solutions["preventive"]:
                        content_parts.append(f"- {measure}")
                    content_parts.append("")
            
            # 诊断结论
            if record.conclusion:
                content_parts.append("## 诊断结论")
                content_parts.append(record.conclusion)
                content_parts.append("")
            
            # 关联信息
            content_parts.append("## 关联信息")
            if record.knowledge_refs:
                content_parts.append(f"- **知识库引用**: {record.knowledge_refs}")
            if record.knowledge_source:
                content_parts.append(f"- **知识来源**: {record.knowledge_source}")
            content_parts.append("")
            
            content = "\n".join(content_parts)
            
            # 3. 构建索引文档
            doc_id = f"diagnosis_{record.id}"
            tags = [
                f"cluster:{cluster.name}",
                f"namespace:{record.namespace or 'default'}",
                f"resource_type:{record.resource_type}",
                f"resource_name:{record.resource_name}",
                "diagnosis_case",
            ]
            
            # 添加指标模式标签（如果有）
            if record.metrics:
                tags.append("has_metrics")
            if record.logs:
                tags.append("has_logs")
            
            # 构建元数据
            metadata = {
                "diagnosis_id": record.id,
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "namespace": record.namespace,
                "resource_type": record.resource_type,
                "resource_name": record.resource_name,
                "confidence": float(record.confidence) if record.confidence else 0.0,
                "knowledge_source": record.knowledge_source,
                "diagnosis_date": record.started_at.isoformat() if record.started_at else None,
            }
            
            # 4. 索引到 OpenSearch（使用诊断案例专用的知识库ID，如果配置了的话）
            knowledge_base_id = settings.OBSERVABILITY_KNOWLEDGE_BASE_ID
            if not knowledge_base_id:
                # 如果没有配置，跳过知识沉淀（不影响诊断流程）
                logger.debug("未配置 OBSERVABILITY_KNOWLEDGE_BASE_ID，跳过知识沉淀")
                return
            
            chunk_data = {
                "document_id": 0,  # 诊断案例没有对应的文档ID
                "knowledge_base_id": knowledge_base_id,
                "chunk_id": record.id,  # 使用诊断记录ID作为chunk_id
                "content": content,
                "chunk_type": "text",
                "tags": tags,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            # 索引到 OpenSearch
            await self.opensearch_service.index_document_chunk(chunk_data)
            
            logger.info(f"诊断案例已保存到知识库: diagnosis_id={record.id}, knowledge_base_id={knowledge_base_id}")
            
            # 5. 更新诊断记录，标记已沉淀到知识库
            record_metadata = record.symptoms or {}
            record_metadata["knowledge_sedimented"] = True
            record_metadata["knowledge_base_id"] = knowledge_base_id
            record_metadata["knowledge_doc_id"] = doc_id
            record.symptoms = record_metadata
            
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"知识沉淀失败: {exc}", exc_info=True)
            # 不抛出异常，避免影响诊断流程
