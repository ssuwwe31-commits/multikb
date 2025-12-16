"""
Simple rule engine for diagnosis workflow.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class DiagnosisRuleService:
    """Evaluate predefined rules against metrics/logs/context."""

    CPU_THRESHOLD = 0.8  # 80% usage
    MEMORY_THRESHOLD_BYTES = 1.5 * 1024 * 1024 * 1024  # 1.5GiB
    RESTART_THRESHOLD = 1.0  # restarts per 5 minutes

    def evaluate(
        self,
        resource_type: str,
        context: Dict[str, Any],
        api_data: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        根据资源类型，应用相应的规则
        
        Args:
            resource_type: 资源类型（pods, nodes, deployments, services 等）
            context: 上下文信息
            api_data: 从 API Server 获取的资源状态和配置
            metrics: 指标数据
            logs: 日志数据
        """
        findings: List[Dict[str, Any]] = []
        
        # 根据资源类型选择规则集
        if resource_type == "pods":
            findings.extend(self._evaluate_pod_rules(context, api_data, metrics, logs))
        elif resource_type == "nodes":
            findings.extend(self._evaluate_node_rules(context, api_data, metrics, logs))
        elif resource_type == "services":
            findings.extend(self._evaluate_service_rules(context, api_data, metrics, logs))
        elif resource_type in ["deployments", "statefulsets", "daemonsets"]:
            findings.extend(self._evaluate_deployment_rules(context, api_data, metrics, logs))
        else:
            # 其他资源类型暂不支持规则检测
            pass
        
        return findings

    def _evaluate_pod_rules(
        self,
        context: Dict[str, Any],
        api_data: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Pod 相关规则"""
        findings: List[Dict[str, Any]] = []
        
        # 检查 Pod 状态
        status = api_data.get("status", {})
        phase = status.get("phase", "").lower()
        if phase in ["pending", "failed", "unknown"]:
            findings.append(
                {
                    "rule": "POD_UNHEALTHY",
                    "severity": "critical",
                    "message": f"Pod 状态异常: {phase}",
                    "evidence": {"phase": phase},
                }
            )
        
        # 检查容器状态
        container_statuses = status.get("containerStatuses", [])
        for container_status in container_statuses:
            state = container_status.get("state", {})
            if "waiting" in state:
                reason = state["waiting"].get("reason", "")
                if reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
                    findings.append(
                        {
                            "rule": f"POD_{reason.upper()}",
                            "severity": "critical",
                            "message": f"容器状态异常: {reason}",
                            "evidence": {"reason": reason, "container": container_status.get("name")},
                        }
                    )
        
        # 检查指标
        findings.extend(self._evaluate_pod_metrics(metrics))
        
        # 检查日志
        findings.extend(self._evaluate_pod_logs(logs))
        
        return findings

    def _evaluate_pod_metrics(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Pod 指标规则"""
        findings: List[Dict[str, Any]] = []
        cpu_value = self._extract_latest_value(metrics.get("pod_cpu_usage"))
        if cpu_value is not None and cpu_value > self.CPU_THRESHOLD:
            findings.append(
                {
                    "rule": "HIGH_CPU_USAGE",
                    "severity": "warning",
                    "message": f"Pod CPU 使用率达到 {cpu_value:.2%}",
                    "evidence": {"cpu_usage": cpu_value, "threshold": self.CPU_THRESHOLD},
                }
            )

        memory_value = self._extract_latest_value(metrics.get("pod_memory_usage"))
        if memory_value is not None and memory_value > self.MEMORY_THRESHOLD_BYTES:
            findings.append(
                {
                    "rule": "HIGH_MEMORY_USAGE",
                    "severity": "warning",
                    "message": f"Pod 内存使用超过 {self.MEMORY_THRESHOLD_BYTES / (1024**3):.1f}GiB",
                    "evidence": {"memory_usage": memory_value},
                }
            )

        restart_rate = self._extract_latest_value(metrics.get("pod_restart_rate"))
        if restart_rate is not None and restart_rate > self.RESTART_THRESHOLD:
            findings.append(
                {
                    "rule": "RESTART_LOOP",
                    "severity": "critical",
                    "message": "容器重启频繁，可能处于 CrashLoopBackOff",
                    "evidence": {"restart_rate": restart_rate},
                }
            )
        return findings

    def _evaluate_pod_logs(self, logs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Pod 日志规则"""
        findings: List[Dict[str, Any]] = []
        if not logs:
            return findings
        text = str(logs)
        if "OOMKilled" in text or "OutOfMemory" in text:
            findings.append(
                {
                    "rule": "LOG_OOM",
                    "severity": "critical",
                    "message": "日志中发现 OOMKilled 关键字，建议检查内存配置",
                }
            )
        if "CrashLoopBackOff" in text:
            findings.append(
                {
                    "rule": "LOG_CRASH_LOOP",
                    "severity": "warning",
                    "message": "日志中出现 CrashLoopBackOff，需排查容器启动逻辑",
                }
            )
        return findings

    def _evaluate_node_rules(
        self,
        context: Dict[str, Any],
        api_data: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Node 相关规则"""
        findings: List[Dict[str, Any]] = []
        
        # 检查 Node 状态
        status = api_data.get("status", {})
        conditions = status.get("conditions", [])
        for condition in conditions:
            condition_type = condition.get("type", "")
            status_value = condition.get("status", "").lower()
            if condition_type == "Ready" and status_value != "true":
                findings.append(
                    {
                        "rule": "NODE_NOT_READY",
                        "severity": "critical",
                        "message": "节点状态为 NotReady",
                        "evidence": {"condition": condition},
                    }
                )
            elif condition_type in ["MemoryPressure", "DiskPressure", "PIDPressure"]:
                if status_value == "true":
                    findings.append(
                        {
                            "rule": f"NODE_{condition_type.upper()}",
                            "severity": "warning",
                            "message": f"节点存在 {condition_type} 压力",
                            "evidence": {"condition": condition},
                        }
                    )
        
        # 检查指标
        cpu_value = self._extract_latest_value(metrics.get("node_cpu_usage"))
        if cpu_value is not None and cpu_value > self.CPU_THRESHOLD:
            findings.append(
                {
                    "rule": "NODE_HIGH_CPU",
                    "severity": "warning",
                    "message": f"节点 CPU 使用率达到 {cpu_value:.2%}",
                    "evidence": {"cpu_usage": cpu_value},
                }
            )
        
        return findings

    def _evaluate_service_rules(
        self,
        context: Dict[str, Any],
        api_data: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Service 相关规则"""
        findings: List[Dict[str, Any]] = []
        
        # 检查 Endpoints（从 API Server 获取）
        # 注意：这里需要额外查询 Endpoints 资源，暂时跳过
        
        # 检查指标
        connection_count = self._extract_latest_value(metrics.get("service_connection_count"))
        if connection_count is not None and connection_count == 0:
            findings.append(
                {
                    "rule": "SERVICE_NO_CONNECTIONS",
                    "severity": "warning",
                    "message": "Service 没有连接，可能无法访问",
                    "evidence": {"connection_count": connection_count},
                }
            )
        
        return findings

    def _evaluate_deployment_rules(
        self,
        context: Dict[str, Any],
        api_data: Dict[str, Any],
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Deployment 相关规则"""
        findings: List[Dict[str, Any]] = []
        
        # 检查副本状态（从 API Server 获取）
        status = api_data.get("status", {})
        spec = api_data.get("spec", {})
        replicas = spec.get("replicas", 0)
        ready_replicas = status.get("readyReplicas", 0)
        available_replicas = status.get("availableReplicas", 0)
        
        if ready_replicas < replicas:
            findings.append(
                {
                    "rule": "DEPLOYMENT_REPLICAS_NOT_READY",
                    "severity": "warning",
                    "message": f"Deployment 副本未就绪: {ready_replicas}/{replicas}",
                    "evidence": {
                        "replicas": replicas,
                        "ready_replicas": ready_replicas,
                        "available_replicas": available_replicas,
                    },
                }
            )
        
        return findings

    @staticmethod
    def _extract_latest_value(metric_payload: Optional[Dict[str, Any]]) -> Optional[float]:
        if not metric_payload:
            return None
        data = metric_payload.get("data", {})
        result = data.get("result") or []
        if not result:
            return None
        # 取第一个系列的最后一个数据点
        series = result[0]
        values = series.get("values") or []
        if not values:
            value = series.get("value")
            if value and len(value) >= 2:
                return float(value[1])
            return None
        latest = values[-1]
        if latest and len(latest) >= 2:
            try:
                return float(latest[1])
            except (TypeError, ValueError):
                return None
        return None
