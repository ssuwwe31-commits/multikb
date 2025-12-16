"""
Diagnosis summary service.
负责生成诊断摘要和解决方案
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List

from app.models.cluster_config import ClusterConfig


class DiagnosisSummaryService:
    """诊断摘要服务"""

    @staticmethod
    def _extract_metric_values(entry: Any) -> List[Any]:
        """兼容不同结构的 Prometheus 返回值，统一取出 values 列表"""
        if not isinstance(entry, dict):
            return []
        values = entry.get("values")
        if isinstance(values, list):
            return values
        data = entry.get("data")
        if isinstance(data, dict):
            results = data.get("result")
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, dict):
                    if "values" in first and isinstance(first["values"], list):
                        return first["values"]
                    value = first.get("value")
                    if isinstance(value, list):
                        return [value]
        return []

    @staticmethod
    def build_reasoning_prompt(
        cluster: ClusterConfig,
        context: Dict[str, Any],
        trigger_payload: Optional[Dict[str, Any]],
        prior_memory_summaries: Optional[List[str]] = None,
    ) -> str:
        """构建推理 Prompt"""
        lines = [
            f"集群名称: {cluster.name}",
            f"集群ID: {context.get('cluster_id')}",
            f"资源类型: {context.get('resource_type')}",
            f"资源: {context.get('namespace') or 'default'}/{context.get('resource_name')}",
        ]
        if trigger_payload:
            labels = trigger_payload.get("labels")
            annotations = trigger_payload.get("annotations")
            lines.append(f"告警标签: {labels}" if labels else "告警标签: 无")
            if annotations:
                lines.append(f"告警注解: {annotations}")
        if prior_memory_summaries:
            lines.append("历史上下文摘要：")
            for item in prior_memory_summaries:
                lines.append(f"- {item}")
        return "\n".join(lines)

    @staticmethod
    def generate_summary_enhanced(
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
        knowledge_refs: Optional[Any],
        rule_findings: List[Dict[str, Any]],
        llm_result: Optional[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str, float, Optional[str], Optional[Dict], Optional[Dict], Optional[Dict]]:
        """
        生成增强的诊断摘要，支持结构化 LLM 输出
        
        Returns:
            (summary, conclusion, confidence, root_cause, timeline, impact_scope, solutions)
        """
        # 如果 LLM 返回结构化结果，优先使用
        if isinstance(llm_result, dict) and "root_cause" in llm_result:
            problem_desc = llm_result.get("problem_description", "")
            root_cause = llm_result.get("root_cause", "")
            confidence = float(llm_result.get("confidence", 0.5))
            timeline = llm_result.get("timeline")
            impact_scope = llm_result.get("impact_scope")
            solutions = llm_result.get("solutions")
            
            # 如果置信度 >= 0.8，清理不确定的描述（可能、大概、或许、也许等）
            if confidence >= 0.8:
                # 移除不确定的描述词
                uncertainty_words = ["可能", "大概", "或许", "也许", "似乎", "看起来", "估计", "推测"]
                for word in uncertainty_words:
                    problem_desc = problem_desc.replace(f"{word} ", "").replace(f" {word}", "").replace(word, "")
                    root_cause = root_cause.replace(f"{word} ", "").replace(f" {word}", "").replace(word, "")
                # 移除多余的空格
                problem_desc = " ".join(problem_desc.split())
                root_cause = " ".join(root_cause.split())
            
            # 构建摘要
            statements = []
            if problem_desc:
                statements.append(problem_desc)
            if root_cause:
                statements.append(f"根因：{root_cause}")
            if not statements:
                statements.append("LLM 已进行系统化分析")
            
            summary = " ".join(statements)
            conclusion = root_cause or "根据系统化分析得出的诊断结论"
            
            return summary, conclusion, confidence, root_cause, timeline, impact_scope, solutions
        
        # 向后兼容：如果 LLM 返回文本或未启用，使用传统方法
        statements = []
        if metrics:
            statements.append("收集到 Prometheus 指标数据，可用于分析资源使用情况。")
        if logs:
            statements.append("已获取最近的日志输出，可进一步排查错误。")
        if knowledge_refs:
            statements.append("找到相关知识条目，建议查看历史案例。")
        if rule_findings:
            statements.extend([finding["message"] for finding in rule_findings])
        if isinstance(llm_result, dict) and "text_insight" in llm_result:
            statements.append(f"LLM 辅助分析: {llm_result['text_insight']}")
        elif isinstance(llm_result, str):
            statements.append(f"LLM 辅助分析: {llm_result}")
        if not statements:
            statements.append("未能获取足够的指标或日志信息，请人工介入。")

        summary = " ".join(statements)
        conclusion = "综合指标、日志、规则与知识库信息，给出初步诊断，请结合业务实际确认。"

        confidence = 0.4
        if metrics:
            confidence += 0.2
        if knowledge_refs:
            confidence += 0.2
        if rule_findings:
            confidence += 0.1
            if any(f.get("severity") == "critical" for f in rule_findings):
                confidence += 0.1
        if llm_result:
            confidence += 0.05
        
        # 如果没有结构化输出，尝试从规则结果生成基础解决方案
        solutions = None
        if rule_findings:
            solutions = DiagnosisSummaryService.generate_basic_solutions_from_rules(rule_findings, context or {})
        
        confidence = max(0.1, min(1.0, confidence))
        return summary, conclusion, confidence, None, None, None, solutions

    @staticmethod
    def generate_basic_solutions_from_rules(
        rule_findings: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于规则结果生成基础解决方案"""
        immediate = []
        root = []
        preventive = []
        
        for finding in rule_findings:
            rule = finding.get("rule", "")
            if rule == "HIGH_CPU_USAGE":
                immediate.append({
                    "title": "重启 Pod 以缓解 CPU 压力",
                    "priority": "high",
                    "steps": [
                        {
                            "step": 1,
                            "action": "kubectl",
                            "command": f"kubectl delete pod {context.get('resource_name', 'POD_NAME')} -n {context.get('namespace', 'default')}",
                            "description": "删除异常 Pod，让 Deployment 自动重建"
                        }
                    ],
                    "risk": "low",
                })
                root.append({
                    "title": "添加 CPU 资源限制",
                    "priority": "high",
                    "steps": [
                        {
                            "step": 1,
                            "action": "edit_deployment",
                            "description": "编辑 Deployment，添加 resources.limits.cpu",
                            "config": {"resources": {"limits": {"cpu": "2"}}}
                        }
                    ],
                    "risk": "medium",
                })
            elif rule == "HIGH_MEMORY_USAGE":
                immediate.append({
                    "title": "重启 Pod 以释放内存",
                    "priority": "high",
                    "steps": [
                        {
                            "step": 1,
                            "action": "kubectl",
                            "command": f"kubectl delete pod {context.get('resource_name', 'POD_NAME')} -n {context.get('namespace', 'default')}",
                            "description": "删除异常 Pod，让 Deployment 自动重建"
                        }
                    ],
                    "risk": "low",
                })
                root.append({
                    "title": "添加内存资源限制",
                    "priority": "high",
                    "steps": [
                        {
                            "step": 1,
                            "action": "edit_deployment",
                            "description": "编辑 Deployment，添加 resources.limits.memory",
                            "config": {"resources": {"limits": {"memory": "4Gi"}}}
                        }
                    ],
                    "risk": "medium",
                })
            elif rule == "HIGH_RESTART_RATE":
                root.append({
                    "title": "检查应用代码和配置",
                    "priority": "high",
                    "steps": [
                        {
                            "step": 1,
                            "action": "check_logs",
                            "description": "查看 Pod 日志，定位重启原因"
                        }
                    ],
                    "risk": "low",
                })
        
        preventive.append("添加资源使用监控告警")
        preventive.append("建立资源配额管理流程")
        
        return {
            "immediate": immediate,
            "root": root,
            "preventive": preventive,
        }

    @staticmethod
    def determine_knowledge_source(
        knowledge_refs: Optional[Any],
        knowledge_confidence: float,
        llm_result: Optional[Any],
        rule_findings: List[Dict[str, Any]],
        min_confidence: float = 0.5,
    ) -> Optional[str]:
        """根据实际使用的证据确定知识来源"""
        if knowledge_refs and knowledge_confidence >= min_confidence:
            return "kb"
        if llm_result:
            return "llm"
        if rule_findings:
            return "rules"
        return None

    @staticmethod
    def generate_metric_summary(metrics_data: Dict[str, Any], iteration_no: int) -> str:
        """
        为指标记忆生成有意义的摘要，提取关键发现
        
        Args:
            metrics_data: 指标数据字典
            iteration_no: 迭代序号
            
        Returns:
            包含关键发现的摘要字符串
        """
        if not metrics_data:
            return f"[迭代 {iteration_no}] 未收集到指标数据"
        
        findings = []
        metric_names = []
        
        # 检查 CPU 使用率
        if "pod_cpu_usage" in metrics_data:
            metric_names.append("CPU")
            cpu_data = metrics_data["pod_cpu_usage"]
            values = DiagnosisSummaryService._extract_metric_values(cpu_data)
            if values:
                cpu_values = [
                    float(v[1] if isinstance(v, (list, tuple)) else v)
                    for v in values
                    if isinstance(v, (list, tuple)) and len(v) >= 2
                ]
                if cpu_values:
                    max_cpu = max(cpu_values)
                    avg_cpu = sum(cpu_values) / len(cpu_values)
                    if max_cpu > 0.8:
                        findings.append(f"CPU异常（最高{max_cpu:.1%}，平均{avg_cpu:.1%}，超过80%阈值）")
                    elif max_cpu > 0.6:
                        findings.append(f"CPU偏高（最高{max_cpu:.1%}，平均{avg_cpu:.1%}）")
        
        # 检查内存使用
        if "pod_memory_usage" in metrics_data:
            metric_names.append("内存")
            mem_data = metrics_data["pod_memory_usage"]
            values = DiagnosisSummaryService._extract_metric_values(mem_data)
            if values:
                mem_values = [
                    float(v[1] if isinstance(v, (list, tuple)) else v)
                    for v in values
                    if isinstance(v, (list, tuple)) and len(v) >= 2
                ]
                if mem_values:
                    max_mem = max(mem_values)
                    avg_mem = sum(mem_values) / len(mem_values)
                    # 转换为 GB
                    max_mem_gb = max_mem / (1024 ** 3)
                    avg_mem_gb = avg_mem / (1024 ** 3)
                    threshold_gb = 1.5
                    if max_mem > threshold_gb * (1024 ** 3):
                        findings.append(f"内存异常（最高{max_mem_gb:.2f}GB，平均{avg_mem_gb:.2f}GB，超过{threshold_gb}GB阈值）")
                    elif max_mem > threshold_gb * 0.8 * (1024 ** 3):
                        findings.append(f"内存偏高（最高{max_mem_gb:.2f}GB，平均{avg_mem_gb:.2f}GB）")
        
        # 检查重启率
        if "pod_restart_rate" in metrics_data:
            metric_names.append("重启率")
            restart_data = metrics_data["pod_restart_rate"]
            values = DiagnosisSummaryService._extract_metric_values(restart_data)
            if values:
                restart_values = [
                    float(v[1] if isinstance(v, (list, tuple)) else v)
                    for v in values
                    if isinstance(v, (list, tuple)) and len(v) >= 2
                ]
                if restart_values:
                    max_restart = max(restart_values)
                    if max_restart > 1.0:
                        findings.append(f"重启频繁（最高{max_restart:.2f}次/5分钟，超过1.0阈值）")
                    elif max_restart > 0.5:
                        findings.append(f"重启较多（最高{max_restart:.2f}次/5分钟）")
        
        if findings:
            return f"[迭代 {iteration_no}] 指标异常：{'; '.join(findings)}"
        
        # 如果没有异常，返回正常状态
        metrics_str = ', '.join(metric_names) if metric_names else ', '.join(metrics_data.keys())
        return f"[迭代 {iteration_no}] 指标正常（{metrics_str}）"

    @staticmethod
    def generate_log_summary(logs_data: Dict[str, Any], iteration_no: int) -> str:
        """
        为日志记忆生成有意义的摘要，提取关键发现
        
        Args:
            logs_data: 日志数据字典
            iteration_no: 迭代序号
            
        Returns:
            包含关键发现的摘要字符串
        """
        if not logs_data:
            return f"[迭代 {iteration_no}] 未收集到日志数据"
        
        logs = logs_data.get("logs", [])
        if not logs:
            return f"[迭代 {iteration_no}] 日志为空"
        
        log_count = len(logs)
        error_keywords = ["error", "fatal", "exception", "panic", "critical", "failed", "failure"]
        warning_keywords = ["warn", "warning", "deprecated"]
        
        error_count = 0
        warning_count = 0
        error_messages = []
        
        for log_entry in logs:
            message = str(log_entry.get("message", "")).lower()
            if any(keyword in message for keyword in error_keywords):
                error_count += 1
                if len(error_messages) < 3:  # 只保存前3条错误消息的摘要
                    error_msg = log_entry.get("message", "")[:50]
                    error_messages.append(error_msg)
            elif any(keyword in message for keyword in warning_keywords):
                warning_count += 1
        
        findings = []
        if error_count > 0:
            error_summary = f"{error_count}条错误"
            if error_messages:
                error_summary += f"（如：{error_messages[0]}...）"
            findings.append(error_summary)
        if warning_count > 0:
            findings.append(f"{warning_count}条警告")
        
        if findings:
            return f"[迭代 {iteration_no}] 日志异常：{'; '.join(findings)}（共{log_count}条）"
        
        return f"[迭代 {iteration_no}] 日志正常（共{log_count}条，无错误）"

    @staticmethod
    def generate_rule_summary(rule_findings: List[Dict[str, Any]], iteration_no: int) -> str:
        """
        为规则记忆生成有意义的摘要，提取关键发现
        
        Args:
            rule_findings: 规则检测结果列表
            iteration_no: 迭代序号
            
        Returns:
            包含关键发现的摘要字符串
        """
        if not rule_findings:
            return f"[迭代 {iteration_no}] 规则检测通过"
        
        critical = [f for f in rule_findings if f.get("severity") == "critical"]
        warnings = [f for f in rule_findings if f.get("severity") == "warning"]
        info = [f for f in rule_findings if f.get("severity") not in ["critical", "warning"]]
        
        findings = []
        if critical:
            critical_messages = [f.get("message", "")[:40] for f in critical[:3]]
            findings.append(f"{len(critical)}个严重问题：{', '.join(critical_messages)}")
        if warnings:
            findings.append(f"{len(warnings)}个警告")
        if info:
            findings.append(f"{len(info)}个提示")
        
        if findings:
            return f"[迭代 {iteration_no}] 规则检测：{'; '.join(findings)}"
        
        return f"[迭代 {iteration_no}] 规则检测通过"
