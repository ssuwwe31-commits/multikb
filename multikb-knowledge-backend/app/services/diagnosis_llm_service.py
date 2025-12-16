"""
Diagnosis LLM service.
负责 LLM 相关的推理和分析
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List
import json
import re

from app.config.settings import settings
from app.core.logging import logger
from app.services.ollama_service import OllamaService


class DiagnosisLlmService:
    """诊断 LLM 服务"""

    def __init__(self, db, ollama_service: OllamaService, rule_service):
        self.db = db
        self.ollama_service = ollama_service
        self.rule_service = rule_service
    
    def _clean_problem_summary(self, text: str) -> str:
        """
        清理问题总结文本，移除无效内容
        
        Args:
            text: LLM返回的原始文本
            
        Returns:
            清理后的问题总结文本
        """
        if not text:
            return ""
        
        cleaned = text.strip()
        
        # 1. 移除思考标签结构
        lower = cleaned.lower()
        # 处理 <think>...</think>
        redacted_start = lower.find("<think>")
        redacted_end = lower.find("</think>")
        if redacted_start != -1 and redacted_end != -1:
            front = cleaned[:redacted_start]
            tail = cleaned[redacted_end + len("</think>") :]
            cleaned = (front + tail).strip()
            lower = cleaned.lower()  # 重新计算lower，因为cleaned已更新
        
        # 处理 <think>...</think>
        think_start = lower.find("<think>")
        think_end = lower.find("</think>")
        if think_start != -1 and think_end != -1:
            front = cleaned[:think_start]
            tail = cleaned[think_end + len("</think>") :]
            cleaned = (front + tail).strip()
        
        # 如果仍包含裸的标签（无闭合），也一并去掉
        cleaned = cleaned.replace("<think>", "").replace("</think>", "")
        cleaned = cleaned.replace("<think>", "").replace("</think>", "")
        
        # 3. 移除常见的说明性前缀文字
        # 移除"好的，我现在需要..."、"首先，我要..."等常见前缀
        prefix_patterns = [
            r"^好的[，,，,].*?生成.*?问题总结",
            r"^首先[，,，,].*?阅读.*?数据",
            r"^我现在需要.*?生成.*?问题总结",
            r"^根据用户提供的信息.*?生成.*?问题总结",
            r"^让我.*?分析.*?数据",
            r"^我需要.*?分析.*?信息",
        ]
        
        for pattern in prefix_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # 4. 移除可能的 markdown 格式
        cleaned = cleaned.replace("**", "").replace("##", "").strip()
        
        # 5. 移除多余的换行和空白
        cleaned = cleaned.replace("\r\n", "\n")
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        
        # 6. 如果清理后为空或过短，尝试提取关键信息
        cleaned = cleaned.strip()
        if len(cleaned) < 10:
            # 尝试从原始文本中提取问题相关信息
            # 查找包含"问题"、"异常"、"错误"等关键词的句子
            sentences = text.split("\n")
            relevant_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if any(keyword in sentence for keyword in ["问题", "异常", "错误", "失败", "Pod", "CPU", "内存", "重启"]):
                    # 跳过明显的说明性文字
                    if not any(prefix in sentence[:20] for prefix in ["好的", "首先", "现在需要", "让我", "我需要"]):
                        relevant_sentences.append(sentence)
            
            if relevant_sentences:
                cleaned = " ".join(relevant_sentences[:3])  # 最多取前3个相关句子
        
        return cleaned.strip()

    async def generate_problem_summary(
        self,
        context: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
        rule_findings: List[Dict[str, Any]],
        api_data: Optional[Dict[str, Any]] = None,
        change_events: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        k8s_resources: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        基于收集到的数据生成问题总结，用于后续知识库搜索
        
        Returns:
            问题总结的文本描述
        """
        if not settings.OLLAMA_MODEL:
            # 如果没有 LLM，使用简单的描述
            resource_name = context.get("resource_name", "未知资源")
            namespace = context.get("namespace", "default")
            return f"Kubernetes {resource_type or 'pod'} {resource_name} 在命名空间 {namespace} 出现问题"
        
        prompt_lines = [
            "你是一名 Kubernetes 运维专家。",
            "请基于以下收集到的数据，生成一个清晰、简洁的问题总结，用于后续搜索相关知识库案例。",
            "问题总结应该包含：问题的关键症状、资源信息、可能的错误类型。",
            "",
            "## 收集到的数据",
            f"资源信息: {context}",
        ]
        
        if api_data:
            prompt_lines.append(f"资源状态和配置: {api_data}")
        
        # 如果提供了扩展的K8s资源信息，添加到prompt中
        if k8s_resources:
            prompt_lines.append("")
            prompt_lines.append("## 扩展的K8s资源信息")
            prompt_lines.append("已收集相关K8s资源信息（Deployment/StatefulSet、Service、ConfigMap/Secret、Node、ResourceQuota、NetworkPolicy、PVC等）：")
            prompt_lines.append(f"{k8s_resources}")
            prompt_lines.append("")
            prompt_lines.append("请特别关注：")
            prompt_lines.append("- Deployment/StatefulSet 配置问题（资源限制、镜像、探针等）")
            prompt_lines.append("- Service 配置问题（端口、选择器、类型等）")
            prompt_lines.append("- ConfigMap/Secret 配置变更或错误")
            prompt_lines.append("- Node 状态问题（资源不足、污点等）")
            prompt_lines.append("- ResourceQuota 限制导致资源不足")
            prompt_lines.append("- NetworkPolicy 网络策略限制")
            prompt_lines.append("- PVC 存储问题")
        
        if metrics:
            prompt_lines.append(f"监控指标: {metrics}")
        
        if logs and logs.get("logs"):
            log_count = len(logs.get("logs", []))
            log_source = logs.get("source", "unknown")
            prompt_lines.append(f"日志信息: 来源={log_source}, 数量={log_count}条")
            
            # 优先提取错误相关的日志（ERROR、WARN、Exception、Failed等）
            error_keywords = ["error", "exception", "failed", "fail", "warn", "warning", 
                            "fatal", "critical", "timeout", "refused", "denied", "closed"]
            error_logs = []
            normal_logs = []
            
            for log in logs.get("logs", []):
                log_message = log.get("message", "").lower()
                if any(keyword in log_message for keyword in error_keywords):
                    error_logs.append(log)
                else:
                    normal_logs.append(log)
            
            # 优先显示错误日志，如果没有错误日志才显示普通日志
            # 注意：错误日志应该完整显示，不要截断，因为关键错误信息可能在后面
            sample_logs = error_logs[:10] if error_logs else normal_logs[:5]  # 增加错误日志数量，完整显示不截断
            if sample_logs:
                log_samples = []
                for log in sample_logs:
                    msg = log.get("message", "")
                    # 错误日志完整显示，不截断，确保包含完整的错误信息
                    # 普通日志可以适当截断
                    if error_logs:
                        log_samples.append(msg)  # 完整错误日志
                    else:
                        # 普通日志截断到500字符（增加长度以保留更多上下文）
                        log_samples.append(msg[:500] if len(msg) > 500 else msg)
                
                if error_logs:
                    prompt_lines.append(f"关键错误日志（优先关注，完整内容）: {log_samples}")
                    prompt_lines.append(f"错误日志总数: {len(error_logs)}条")
                    prompt_lines.append("**重要**：这些错误日志是诊断的关键依据，请仔细分析其中的错误信息（如 UnknownHostException、Connection refused 等），并直接使用这些错误信息作为根因。")
                else:
                    prompt_lines.append(f"日志示例: {log_samples}")
        
        if rule_findings:
            prompt_lines.append(f"规则检测结果: {rule_findings}")
        
        if change_events and change_events.get("changes"):
            changes_count = len(change_events.get("changes", []))
            prompt_lines.append(f"最近资源变更: {changes_count}条")
        
        prompt_lines.extend([
            "",
            "## 要求",
            "请直接生成一个问题总结，格式为：",
            "- 问题类型（如：Pod 启动失败、CPU 异常、内存泄漏、网络异常等）",
            "- 关键症状（如：重启频繁、资源占用高、具体错误信息等）",
            "- 具体错误信息（重要：必须包含日志中的关键错误、异常信息、错误码等，便于搜索匹配）",
            "- 资源信息（Pod/Deployment 名称、命名空间）",
            "",
            "重要提示：",
            "1. 直接输出问题总结，不要包含任何说明性文字（如：'好的，我现在需要...'、'首先，我要...'等）",
            "2. 不要包含思考过程或推理过程",
            "3. 只返回问题总结的文本内容，不要有其他格式或说明",
            "4. 问题总结应该简洁明了，但必须包含具体的错误信息（如异常类型、错误消息、错误码等），这样更容易搜索到相关解决方案",
            "5. 如果日志中包含错误信息，务必在问题总结中明确写出具体的错误内容（如 SocketException、Connection refused 等）"
        ])
        
        try:
            prompt = "\n".join(prompt_lines)
            response = await self.ollama_service.generate_text(prompt)
            if response:
                # 清理响应，提取关键信息
                summary = self._clean_problem_summary(response)
                logger.info(f"[问题总结生成] 生成的问题总结: {summary[:200]}")
                return summary
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(f"生成问题总结失败: {exc}")
        
        # 回退到简单描述
        resource_name = context.get("resource_name", "未知资源")
        namespace = context.get("namespace", "default")
        return f"Kubernetes {resource_type or 'pod'} {resource_name} 在命名空间 {namespace} 出现问题"

    async def evaluate_knowledge_relevance(
        self,
        problem_summary: str,
        knowledge_content: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        评估知识库内容是否符合当前问题的解决方案
        
        Returns:
            Dict 包含：is_relevant (bool), confidence (float), match_reason (str)
        """
        if not settings.OLLAMA_MODEL:
            return {"is_relevant": False, "confidence": 0.0, "match_reason": "LLM未启用"}
        
        prompt_lines = [
            "你是一名 Kubernetes 运维专家。",
            "请评估以下知识库内容是否适用于解决当前问题。",
            "",
            "## 当前问题",
            problem_summary,
            "",
            "## 资源上下文",
            f"{context}",
            "",
            "## 知识库内容",
            knowledge_content[:2000],  # 限制长度
            "",
            "## 要求",
            "请评估知识库内容是否与当前问题相关，并给出置信度（0.0-1.0）。",
            "只返回 JSON 格式：",
            "{",
            '  "is_relevant": true/false,',
            '  "confidence": 0.0-1.0,',
            '  "match_reason": "相关/不相关的原因"',
            "}",
        ]
        
        try:
            prompt = "\n".join(prompt_lines)
            response = await self.ollama_service.generate_text(prompt)
            if response:
                # 尝试解析 JSON
                import json
                import re
                json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info(f"[知识库评估] 评估结果: {result}")
                    return result
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(f"评估知识库相关性失败: {exc}")
        
        # 回退：简单判断是否包含关键词
        resource_name = context.get("resource_name", "").lower()
        problem_keywords = problem_summary.lower().split()
        knowledge_lower = knowledge_content.lower()
        
        keyword_match = sum(1 for keyword in problem_keywords if keyword in knowledge_lower)
        relevance_score = keyword_match / max(len(problem_keywords), 1)
        
        return {
            "is_relevant": relevance_score > 0.3,
            "confidence": min(relevance_score, 1.0),
            "match_reason": f"关键词匹配度: {relevance_score:.2%}"
        }

    async def call_llm(
        self,
        context: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
        rule_findings: List[Dict[str, Any]],
        knowledge_refs: Optional[Any],
        external_refs: Optional[List[Dict[str, Any]]],
        k8s_resources: Optional[Dict[str, Any]] = None,
        deep_context: Optional[Dict[str, Any]] = None,
        prior_memories: Optional[List[Dict[str, Any]]] = None,
        api_data: Optional[Dict[str, Any]] = None,
        change_events: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,  # 添加资源类型参数
    ) -> Optional[Dict[str, Any]]:
        """
        调用 LLM 进行系统化根因分析，返回结构化结果
        
        Args:
            prior_memories: 历史记忆列表，每个记忆包含 memory_type, summary, content, iteration_no
        
        Returns:
            Dict 包含：problem_description, timeline, impact_scope, root_cause_analysis,
                     evidence_chain, root_cause, confidence, solutions, next_action
            如果 LLM 未启用或返回文本，返回 None 或文本字符串（向后兼容）
        """
        if not settings.OLLAMA_MODEL:
            return None
        # 注意：此检查已在调用方（_run_single_iteration）中通过 llm_should_run 判断
        # 如果知识库有命中且规则有发现，调用方会跳过 LLM 调用
        # 如果知识库未命中，即使有规则发现也会调用 LLM 来获取置信度，用于判断是否需要外部搜索
        if knowledge_refs and len(knowledge_refs) >= 1 and rule_findings:
            # 已经有较充分信息，避免多余调用（此检查作为双重保险）
            return None
        
        # 构建增强的结构化 Prompt（包含历史记忆和变更信息）
        prompt = self.build_structured_llm_prompt(
            context, metrics, logs, rule_findings, knowledge_refs, external_refs, 
            k8s_resources, deep_context, prior_memories, api_data, change_events, resource_type
        )
        
        try:
            # 使用 format="json" 强制 Ollama 返回 JSON 格式（对小模型特别有效）
            response = await self.ollama_service.generate_text(prompt, format="json")
            if not response:
                return None
            
            # 尝试解析 JSON 格式的结构化输出
            structured_result = self.parse_llm_structured_output(response)
            if structured_result:
                return structured_result
            
            # 如果解析失败，记录详细信息并尝试提取关键信息
            logger.warning(
                "LLM 返回非结构化文本，无法解析为 JSON。响应长度: %d, 前500字符: %s",
                len(response),
                response[:500] if len(response) > 500 else response
            )
            # 尝试从文本中提取关键信息
            # 至少返回一个基本结构，避免后续代码出错
            return {
                "text_insight": response.strip()[:2000],  # 限制长度
                "problem_description": "LLM 返回了非结构化文本，无法自动解析",
                "confidence": 0.3,  # 低置信度，因为无法解析
                "root_cause": "无法解析 LLM 输出",
                "parsing_error": True
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LLM 诊断失败: %s", exc)
            return None

    def build_structured_llm_prompt(
        self,
        context: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
        rule_findings: List[Dict[str, Any]],
        knowledge_refs: Optional[Any],
        external_refs: Optional[List[Dict[str, Any]]],
        k8s_resources: Optional[Dict[str, Any]] = None,
        deep_context: Optional[Dict[str, Any]] = None,
        prior_memories: Optional[List[Dict[str, Any]]] = None,
        api_data: Optional[Dict[str, Any]] = None,
        change_events: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,  # 添加资源类型参数
    ) -> str:
        """构建结构化的 LLM Prompt，要求系统化分析"""
        prompt_lines = [
            "你是一名 Kubernetes 运维专家，请使用系统化的方法分析问题。",
            "",
            "## 输入信息",
            f"上下文: {context}",
        ]
        
        # 添加 API Server 数据（资源状态和配置）
        if api_data:
            prompt_lines.append(f"资源状态和配置（API Server）: {api_data}")
        
        # 添加资源变更信息（重要：用于关联问题与配置变更）
        if change_events and change_events.get("changes"):
            changes = change_events.get("changes", [])
            prompt_lines.append("")
            prompt_lines.append("## 最近资源变更信息（问题发生前 24 小时）")
            prompt_lines.append("以下变更可能与当前问题相关，请重点关注：")
            for i, change in enumerate(changes[:20], 1):  # 最多显示 20 条
                change_type = change.get("resource_type", "unknown")
                change_name = change.get("resource_uid", "unknown")
                event_type = change.get("event_type", "unknown")
                created_at = change.get("created_at", "")
                diff = change.get("diff", {})
                
                prompt_lines.append(f"{i}. [{event_type}] {change_type}/{change_name} (时间: {created_at})")
                if diff:
                    # 简化 diff 显示，只显示关键字段
                    simplified_diff = {}
                    for key, value in diff.items():
                        if isinstance(value, dict) and "before" in value and "after" in value:
                            before_str = str(value.get("before", ""))[:50]
                            after_str = str(value.get("after", ""))[:50]
                            simplified_diff[key] = f"变更: {before_str} -> {after_str}"
                    if simplified_diff:
                        prompt_lines.append(f"   变更内容: {simplified_diff}")
            prompt_lines.append("")
            prompt_lines.append("**重要提示**：请分析这些变更是否可能导致当前问题，特别是：")
            prompt_lines.append("1. ConfigMap/Secret 配置变更可能导致应用行为异常")
            prompt_lines.append("2. Deployment/Pod 配置变更可能导致资源不足或启动失败")
            prompt_lines.append("3. 变更时间与问题发生时间的关联性")
        
        # 添加监控和日志系统的状态说明
        monitoring_status = ""
        if isinstance(metrics, dict):
            if metrics.get("monitoring_configured") is False:
                monitoring_status = "**监控系统状态**: 未配置（未设置 Prometheus URL）"
            elif metrics.get("monitoring_configured") is True:
                # 先检查是否有实际数据（优先检查实际数据，而不是 message）
                has_data = any(
                    key not in ["monitoring_configured", "time_range", "message"]
                    and v 
                    and isinstance(v, dict) 
                    and v.get("data", {})
                    and v.get("data", {}).get("result")
                    and isinstance(v.get("data", {}).get("result"), list)
                    and len(v.get("data", {}).get("result", [])) > 0
                    for key, v in metrics.items()
                )
                
                message = metrics.get("message", "")
                if has_data:
                    # 如果有数据，优先显示数据状态，然后显示 message（如果有）
                    if message and ("成功获取" in message or "数据正常" in message):
                        monitoring_status = f"**监控系统状态**: 已配置，{message}"
                    else:
                        # 统计有数据的指标数量
                        data_keys = [
                            key for key in metrics.keys() 
                            if key not in ["monitoring_configured", "time_range", "message"]
                            and metrics.get(key)
                            and isinstance(metrics.get(key), dict)
                            and metrics.get(key).get("data", {}).get("result")
                            and len(metrics.get(key).get("data", {}).get("result", [])) > 0
                        ]
                        data_count = len(data_keys)
                        monitoring_status = f"**监控系统状态**: 已配置，成功获取 {data_count} 个指标数据"
                elif message:
                    # 如果没有数据但有 message，使用 message
                    monitoring_status = f"**监控系统状态**: 已配置，{message}"
                else:
                    # 既没有数据也没有 message
                    monitoring_status = "**监控系统状态**: 已配置，但查询无数据（可能是时间范围不对、Pod 刚创建、或查询语法问题）"
        else:
            monitoring_status = "**监控系统状态**: 未知"
        
        log_status = ""
        if isinstance(logs, dict):
            log_available = logs.get("log_available", False)
            log_system_configured = logs.get("log_system_configured", False)
            source = logs.get("source")
            error = logs.get("error")
            log_count = len(logs.get("logs", []))
            
            if log_available or source == "k8s_api":
                log_status = f"**日志获取状态**: 可以通过 K8s API 获取（已获取 {log_count} 条日志）"
            elif log_system_configured:
                if error:
                    log_status = f"**日志获取状态**: 日志系统已配置，但查询失败 - {error}"
                elif log_count > 0:
                    log_status = f"**日志获取状态**: 日志系统已配置，已获取 {log_count} 条日志"
                else:
                    log_status = "**日志获取状态**: 日志系统已配置，但查询无数据（可能是时间范围不对、或该资源确实无日志）"
            else:
                if resource_type == "pods":
                    log_status = "**日志获取状态**: Pod 日志可以通过 K8s API 获取（无需日志系统）。如果 Pod 不在运行状态，需要日志系统获取历史日志。"
                else:
                    log_status = "**日志获取状态**: 日志系统未配置，无法获取日志"
        
        # 打印实际传递给 LLM 的数据摘要
        logger.info("[LLM Prompt] 监控状态: %s", monitoring_status.replace("**", ""))
        logger.info("[LLM Prompt] 日志状态: %s", log_status.replace("**", "") if log_status else f"{logs}")
        
        # 检查指标数据详情
        if isinstance(metrics, dict) and metrics.get("monitoring_configured"):
            for key in metrics.keys():
                if key not in ["monitoring_configured", "time_range", "message"]:
                    metric_data = metrics.get(key, {})
                    if isinstance(metric_data, dict):
                        result_list = metric_data.get("data", {}).get("result", [])
                        if result_list:
                            logger.info(f"[LLM Prompt] 指标 {key} 有数据: {len(result_list)} 个结果")
                        else:
                            logger.warning(f"[LLM Prompt] 指标 {key} 无数据或结果为空")
        
        # 检查日志数据详情
        if isinstance(logs, dict):
            log_count = len(logs.get("logs", []))
            log_source = logs.get("source")
            logger.info(f"[LLM Prompt] 日志数据: 来源={log_source}, 数量={log_count}")
            if log_count == 0 and not logs.get("error"):
                logger.warning("[LLM Prompt] 日志数量为0且无错误信息，可能需要检查日志收集逻辑")
        
        prompt_lines.extend([
            "",
            "## 监控和日志系统状态",
            monitoring_status,
            log_status if log_status else f"**日志获取状态**: {logs}",
            "",
            "## 数据详情",
            f"指标数据: {metrics}",
            f"规则检测结果: {rule_findings}",
        ])
        
        # 重点处理日志信息，明确强调日志中的错误信息是关键证据
        if isinstance(logs, dict) and logs.get("logs"):
            log_list = logs.get("logs", [])
            log_source = logs.get("source", "unknown")
            log_count = len(log_list)
            
            prompt_lines.append("")
            prompt_lines.append("## 日志信息（关键证据 - 优先分析）")
            prompt_lines.append(f"**重要提示**：日志是诊断问题的关键证据，请优先分析日志中的错误信息。")
            prompt_lines.append(f"日志来源: {log_source}, 总数量: {log_count} 条")
            prompt_lines.append("")
            
            # 提取和分类日志
            error_keywords = ["error", "exception", "failed", "fail", "warn", "warning", 
                            "fatal", "critical", "timeout", "refused", "denied", "closed",
                            "unable", "unavailable", "cannot", "can't", "connection", "connect",
                            "resolve", "resolvable", "unknownhost", "dns", "host"]
            
            error_logs = []
            warning_logs = []
            normal_logs = []
            
            for log in log_list:
                msg = str(log.get("message", "")).lower()
                # 检查是否为错误日志
                if any(keyword in msg for keyword in error_keywords):
                    # 进一步判断是 ERROR 还是 WARNING
                    if any(kw in msg for kw in ["error", "exception", "failed", "fatal", "critical"]):
                        error_logs.append(log)
                    else:
                        warning_logs.append(log)
                else:
                    normal_logs.append(log)
            
            # 优先展示错误日志（完整内容，不截断）
            if error_logs:
                prompt_lines.append(f"### 错误日志（共 {len(error_logs)} 条）- **这是诊断的关键依据，请仔细分析**")
                for i, log in enumerate(error_logs[:20], 1):  # 最多显示 20 条错误日志
                    msg = log.get("message", "")
                    timestamp = log.get("timestamp", "")
                    prompt_lines.append(f"{i}. [{timestamp}] {msg}")
                if len(error_logs) > 20:
                    prompt_lines.append(f"   ... 还有 {len(error_logs) - 20} 条错误日志未显示")
            
            # 其次展示警告日志
            if warning_logs:
                prompt_lines.append("")
                prompt_lines.append(f"### 警告日志（共 {len(warning_logs)} 条）")
                for i, log in enumerate(warning_logs[:10], 1):  # 最多显示 10 条警告日志
                    msg = log.get("message", "")
                    timestamp = log.get("timestamp", "")
                    prompt_lines.append(f"{i}. [{timestamp}] {msg}")
                if len(warning_logs) > 10:
                    prompt_lines.append(f"   ... 还有 {len(warning_logs) - 10} 条警告日志未显示")
            
            # 如果需要，展示少量普通日志作为上下文
            if not error_logs and not warning_logs and normal_logs:
                prompt_lines.append("")
                prompt_lines.append("### 普通日志（作为上下文参考）")
                for i, log in enumerate(normal_logs[:5], 1):
                    msg = log.get("message", "")
                    timestamp = log.get("timestamp", "")
                    prompt_lines.append(f"{i}. [{timestamp}] {msg}")
            
            prompt_lines.append("")
            prompt_lines.append("**关键要求**：")
            prompt_lines.append("1. **必须优先分析日志中的错误信息**，这是诊断问题的直接证据")
            prompt_lines.append("2. 如果日志中明确显示某个错误（如连接失败、域名解析失败、超时等），**必须将此作为根因分析的主要依据**")
            prompt_lines.append("3. 根因结论应直接基于日志中的错误信息，而不是推测配置问题")
            prompt_lines.append("4. 如果日志显示 'Unable to resolve address'、'UnknownHostException'、'Connection refused'、'Timeout' 等错误，这些就是问题的直接原因")
            prompt_lines.append("5. 只有在日志中没有明确错误信息时，才需要分析配置、指标等其他信息")
        else:
            # 如果没有日志，也要说明
            prompt_lines.append("")
            prompt_lines.append("## 日志信息")
            if isinstance(logs, dict) and logs.get("error"):
                prompt_lines.append(f"**日志获取失败**: {logs.get('error')}")
            else:
                prompt_lines.append("**未获取到日志信息**")
        
        # 添加历史记忆上下文
        if prior_memories:
            prompt_lines.append("")
            prompt_lines.append("## 历史诊断上下文")
            prompt_lines.append("以下是之前迭代收集的关键信息，请结合当前数据进行对比分析：")
            for memory in prior_memories:
                memory_type = memory.get("memory_type", "")
                summary = memory.get("summary", "")
                content = memory.get("content", {})
                iteration_no = memory.get("iteration_no", "?")
                
                if memory_type == "metric" and content:
                    # 提取历史指标的关键值
                    key_points = self._extract_metric_key_points(content)
                    if key_points:
                        prompt_lines.append(f"- [迭代 {iteration_no}] 历史指标：{summary}")
                        prompt_lines.append(f"  关键数据：{key_points}")
                elif memory_type == "log" and content:
                    # 提取历史日志的关键信息
                    key_points = self._extract_log_key_points(content)
                    if key_points:
                        prompt_lines.append(f"- [迭代 {iteration_no}] 历史日志：{summary}")
                        prompt_lines.append(f"  关键信息：{key_points}")
                elif memory_type == "rule" and content:
                    # 提取历史规则发现
                    key_points = self._extract_rule_key_points(content)
                    if key_points:
                        prompt_lines.append(f"- [迭代 {iteration_no}] 历史规则发现：{summary}")
                        prompt_lines.append(f"  关键问题：{key_points}")
                elif memory_type == "llm" and content:
                    # 提取历史 LLM 推理结论
                    root_cause = content.get("root_cause", "")
                    confidence = content.get("confidence", 0)
                    if root_cause:
                        prompt_lines.append(f"- [迭代 {iteration_no}] 历史推理结论：{summary}")
                        prompt_lines.append(f"  根因分析：{root_cause[:200]}")
                        if confidence:
                            prompt_lines.append(f"  置信度：{confidence:.2%}")
            
            prompt_lines.append("")
            prompt_lines.append("请特别注意：")
            prompt_lines.append("1. 对比当前数据与历史数据，判断问题是否在恶化或改善")
            prompt_lines.append("2. 基于历史发现，重点关注可能相关的指标和日志")
            prompt_lines.append("3. 如果历史推理未找到根因，请尝试从不同角度分析")
            prompt_lines.append("4. 识别指标趋势（如CPU/内存是否持续上升）")
        
        if knowledge_refs:
            prompt_lines.append(f"知识库参考: {knowledge_refs}")
        if external_refs:
            prompt_lines.append(f"外部搜索参考: {external_refs}")
        if k8s_resources:
            prompt_lines.append(f"相关 K8s 资源信息: {k8s_resources}")
            prompt_lines.append("")
            prompt_lines.append("注意：如果 Pod 级别诊断未找到根因，请重点分析上述 K8s 资源信息，")
            prompt_lines.append("包括 Deployment/StatefulSet 配置、Service 配置、ConfigMap/Secret、")
            prompt_lines.append("Node 状态、ResourceQuota 限制、NetworkPolicy、PVC 等，")
            prompt_lines.append("这些资源的问题可能导致 Pod 异常。")
        
        if deep_context:
            prompt_lines.append(f"深度上下文信息: {deep_context}")
            prompt_lines.append("")
            prompt_lines.append("注意：这是深度诊断收集的额外信息，包括：")
            prompt_lines.append("- K8s Events：显示资源变化历史")
            prompt_lines.append("- 同一 Deployment 下的其他 Pod：用于对比分析")
            prompt_lines.append("- 同一节点上的其他 Pod：判断是否是节点级别问题")
            prompt_lines.append("- 命名空间统计：了解整体环境状态")
            prompt_lines.append("请综合分析这些信息，找出问题的根本原因。")
        
        prompt_lines.extend([
            "",
            "## 重要要求：",
            "1. **日志优先原则**：必须优先分析日志中的错误信息，这是诊断问题的直接证据。如果日志中有明确的错误（如 'UnknownHostException'、'Unable to resolve address'、'Connection refused'、'Timeout' 等），必须直接使用这些错误信息作为根因，而不是推测配置问题。",
            "2. **根因分析顺序**：",
            "   a) 首先分析日志中的错误信息（最直接、最可靠）",
            "   b) 如果日志没有明确错误，再分析指标数据",
            "   c) 如果日志和指标都无法确定根因，再分析配置信息",
            "   d) 避免在没有证据的情况下推测配置问题（如 setup.sh 脚本错误）",
            "3. 请根据分析结果给出置信度（0-1之间的小数），置信度应反映分析的确定性",
            "4. 如果置信度 >= 0.8，请在问题描述和根因结论中使用肯定的语气，不使用'可能'、'大概'、'或许'、'也许'、'似乎'、'看起来'、'估计'、'推测'等不确定的描述",
            "5. 如果置信度 < 0.8，可以使用不确定的描述，但应说明不确定性来源",
            "6. 问题描述和根因结论应基于证据链，证据充分时使用肯定语气，证据不足时使用不确定语气",
            "7. **示例**：如果日志显示 'UnknownHostException: zk-hs.kaka.svc.cluster.local'，根因应该是 '无法解析 ZooKeeper 域名 zk-hs.kaka.svc.cluster.local'，而不是推测 'setup.sh 脚本错误'",
            "",
            "## 请按以下结构分析并返回 JSON 格式结果：",
            "",
            "{",
            '  "problem_description": "清晰描述当前问题（What），如果置信度>=0.8，使用肯定语气，不使用"可能"、"大概"等不确定描述",',
            '  "timeline": {',
            '    "problem_start": "问题开始时间（ISO格式）",',
            '    "problem_escalate": "问题恶化时间（ISO格式）",',
            '    "key_events": ["关键事件1", "关键事件2"]',
            "  },",
            '  "impact_scope": {',
            '    "affected_pods": ["pod名称列表"],',
            '    "affected_services": ["service名称列表"],',
            '    "affected_nodes": ["node名称列表"],',
            '    "business_impact": "high/medium/low"',
            "  },",
            '  "root_cause_analysis": {',
            '    "why1": "为什么1（直接原因）",',
            '    "why2": "为什么2",',
            '    "why3": "为什么3",',
            '    "why4": "为什么4",',
            '    "why5": "为什么5（根本原因）"',
            "  },",
            '  "evidence_chain": {',
            '    "logs": ["关键错误日志（优先证据）- 必须包含具体的错误信息，如 UnknownHostException、Connection refused 等"],',
            '    "metrics": {"关键指标": "值"},',
            '    "config": {"配置问题": "详情（只有在日志中没有明确错误时才需要）"},',
            '    "events": ["关键事件"]',
            "  },",
            '  "root_cause": "基于证据链得出的根因结论。**重要**：如果日志中有明确的错误信息（如连接失败、域名解析失败），必须直接使用日志中的错误作为根因，而不是推测其他配置问题。如果置信度>=0.8，使用肯定语气，不使用"可能"、"大概"等不确定描述",',
            '  "confidence": 0.85,',
            '  "solutions": {',
            '    "immediate": [',
            "      {",
            '        "title": "立即缓解措施标题",',
            '        "priority": "high/medium/low",',
            '        "steps": [',
            "          {",
            '            "step": 1,',
            '            "action": "kubectl/edit_config/script",',
            '            "command": "具体命令（如果是kubectl）",',
            '            "config": {"配置修改内容"},',
            '            "description": "步骤说明"',
            "          }",
            "        ],",
            '        "risk": "low/medium/high",',
            '        "rollback": {"command": "回滚命令", "description": "回滚说明"},',
            '        "verification": {',
            '          "metrics": ["需要验证的指标"],',
            '          "expected": "预期结果",',
            '          "timeout": 300',
            "        }",
            "      }",
            "    ],",
            '    "root": [',
            "      {",
            '        "title": "根本解决方案标题",',
            '        "priority": "high/medium/low",',
            '        "steps": [...],',
            '        "risk": "low/medium/high",',
            '        "verification": {...}',
            "      }",
            "    ],",
            '    "preventive": ["预防措施1", "预防措施2"]',
            "  },",
            '  "next_action": "completed/collect_more_logs/pending_human"',
            "}",
            "",
            "## ⚠️ 重要：输出格式要求",
            "1. **必须只返回 JSON 格式**，不要包含任何其他文字说明、解释或思考过程",
            "2. **不要使用 markdown 代码块**（不要使用 ```json 或 ``` 包裹）",
            "3. **直接返回 JSON 对象**，从 { 开始，到 } 结束",
            "4. **确保 JSON 格式正确**：所有字符串用双引号，数字不加引号，布尔值使用 true/false",
            "5. **示例正确格式**：",
            '   {"problem_description": "Pod 启动失败", "confidence": 0.85, ...}',
            "",
            "请严格按照上述要求，只返回 JSON 格式，不要包含任何其他内容。",
        ])
        return "\n".join(prompt_lines)

    def parse_llm_structured_output(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 的结构化 JSON 输出
        
        支持多种解析策略，处理小模型可能返回的非标准 JSON 格式
        """
        if not response or not response.strip():
            logger.warning("LLM 返回空响应")
            return None
        
        # 清理响应：移除前后空白和可能的说明文字
        response = response.strip()
        
        # 移除常见的说明性前缀（小模型可能会添加）
        prefixes_to_remove = [
            r'^好的[，,，,].*?\n',
            r'^根据.*?分析[，,，,].*?\n',
            r'^以下是.*?分析结果[：:]\s*\n',
            r'^分析结果如下[：:]\s*\n',
        ]
        for pattern in prefixes_to_remove:
            response = re.sub(pattern, '', response, flags=re.IGNORECASE | re.MULTILINE)
        response = response.strip()
        
        # 方法1：尝试直接解析（如果已经是纯 JSON）
        try:
            result = json.loads(response)
            if isinstance(result, dict) and ("root_cause" in result or "problem_description" in result):
                logger.debug("成功直接解析 JSON（纯 JSON 格式）")
                return result
        except json.JSONDecodeError:
            pass
        
        # 方法2：尝试提取 markdown 代码块中的 JSON（如果 LLM 使用了代码块）
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                result = json.loads(json_str)
                if isinstance(result, dict) and ("root_cause" in result or "problem_description" in result):
                    logger.debug("成功从 markdown 代码块中解析 JSON")
                    return result
            except json.JSONDecodeError as exc:
                logger.debug("从 markdown 代码块解析 JSON 失败: %s", exc)
        
        # 方法3：尝试查找 JSON 对象（从第一个 { 到最后一个 }）
        # 使用平衡括号算法找到完整的 JSON 对象
        json_str = self._extract_json_object(response)
        if json_str:
            try:
                result = json.loads(json_str)
                if isinstance(result, dict) and ("root_cause" in result or "problem_description" in result):
                    logger.debug("成功提取并解析 JSON 对象")
                    return result
            except json.JSONDecodeError as exc:
                logger.debug("提取的 JSON 字符串解析失败: %s", exc)
                # 尝试修复常见的 JSON 错误
                json_str_fixed = self._fix_common_json_errors(json_str)
                if json_str_fixed:
                    try:
                        result = json.loads(json_str_fixed)
                        if isinstance(result, dict) and ("root_cause" in result or "problem_description" in result):
                            logger.info("通过修复常见错误成功解析 JSON")
                            return result
                    except json.JSONDecodeError:
                        pass
        
        # 如果所有方法都失败，记录详细信息以便调试
        logger.warning(
            "无法解析 LLM 输出为 JSON 格式。响应长度: %d, 前300字符: %s, 后300字符: %s",
            len(response),
            response[:300] if len(response) > 300 else response,
            response[-300:] if len(response) > 300 else ""
        )
        return None
    
    def _extract_json_object(self, text: str) -> Optional[str]:
        """从文本中提取完整的 JSON 对象（使用平衡括号算法）"""
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # 使用栈来匹配括号
        stack = []
        for i in range(start_idx, len(text)):
            char = text[i]
            if char == '{':
                stack.append(i)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack:  # 找到匹配的结束括号
                        return text[start_idx:i+1]
        
        # 如果没有找到匹配的结束括号，尝试到文本末尾
        if stack:
            return text[start_idx:]
        
        return None
    
    def _fix_common_json_errors(self, json_str: str) -> Optional[str]:
        """修复常见的 JSON 格式错误"""
        try:
            # 1. 修复单引号问题
            fixed = json_str.replace("'", '"')
            
            # 2. 修复未加引号的键（简单情况）
            # 匹配 pattern: { key: value } -> { "key": value }
            fixed = re.sub(r'(\{|\s|,)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed)
            
            # 3. 修复尾随逗号
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            # 4. 修复注释（移除单行注释）
            fixed = re.sub(r'//.*?$', '', fixed, flags=re.MULTILINE)
            
            # 5. 修复布尔值（Python 风格 -> JSON 风格）
            fixed = re.sub(r'\bTrue\b', 'true', fixed)
            fixed = re.sub(r'\bFalse\b', 'false', fixed)
            fixed = re.sub(r'\bNone\b', 'null', fixed)
            
            return fixed
        except Exception as exc:
            logger.debug("修复 JSON 错误时发生异常: %s", exc)
            return None

    @staticmethod
    def _extract_metric_key_points(metrics_data: Dict[str, Any]) -> str:
        """从指标数据中提取关键点"""
        key_points = []
        if "pod_cpu_usage" in metrics_data:
            cpu_data = metrics_data["pod_cpu_usage"]
            values = cpu_data.get("values", [])
            if values:
                cpu_values = [float(v) for _, v in values if isinstance(v, (int, float))]
                if cpu_values:
                    max_cpu = max(cpu_values)
                    avg_cpu = sum(cpu_values) / len(cpu_values)
                    key_points.append(f"CPU: 最高{max_cpu:.1%}, 平均{avg_cpu:.1%}")
        
        if "pod_memory_usage" in metrics_data:
            mem_data = metrics_data["pod_memory_usage"]
            values = mem_data.get("values", [])
            if values:
                mem_values = [float(v) for _, v in values if isinstance(v, (int, float))]
                if mem_values:
                    max_mem = max(mem_values) / (1024 ** 3)  # 转换为GB
                    avg_mem = sum(mem_values) / len(mem_values) / (1024 ** 3)
                    key_points.append(f"内存: 最高{max_mem:.2f}GB, 平均{avg_mem:.2f}GB")
        
        if "pod_restart_rate" in metrics_data:
            restart_data = metrics_data["pod_restart_rate"]
            values = restart_data.get("values", [])
            if values:
                restart_values = [float(v) for _, v in values if isinstance(v, (int, float))]
                if restart_values:
                    max_restart = max(restart_values)
                    key_points.append(f"重启率: 最高{max_restart:.2f}次/5分钟")
        
        return "; ".join(key_points) if key_points else "无关键数据"

    @staticmethod
    def _extract_log_key_points(logs_data: Dict[str, Any]) -> str:
        """从日志数据中提取关键点"""
        logs = logs_data.get("logs", [])
        if not logs:
            return "无日志"
        
        error_keywords = ["error", "fatal", "exception", "panic", "critical"]
        error_count = sum(1 for log in logs 
                         if any(kw in str(log.get("message", "")).lower() for kw in error_keywords))
        
        if error_count > 0:
            return f"发现{error_count}条错误日志（共{len(logs)}条）"
        return f"日志正常（共{len(logs)}条，无错误）"

    @staticmethod
    def _extract_rule_key_points(rule_findings: List[Dict[str, Any]]) -> str:
        """从规则发现中提取关键点"""
        if not rule_findings:
            return "无规则问题"
        
        critical = [f for f in rule_findings if f.get("severity") == "critical"]
        warnings = [f for f in rule_findings if f.get("severity") == "warning"]
        
        points = []
        if critical:
            points.append(f"{len(critical)}个严重问题")
        if warnings:
            points.append(f"{len(warnings)}个警告")
        
        if points:
            return "; ".join(points)
        return f"{len(rule_findings)}个提示"
