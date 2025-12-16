"""
Diagnosis data collector service.
负责收集诊断所需的数据：指标、日志、知识库搜索、外部搜索
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

import httpx  # type: ignore

from app.config.settings import settings
from app.core.logging import logger
from app.models.cluster_config import ClusterConfig
from app.services.cluster_config_service import ResourceSnapshotService
from app.services.metrics_service import PrometheusMetricsService
from app.services.log_query_service import LogQueryService
from app.services.resource_sync_service import KubernetesResourceSyncService
from app.services.search_service import SearchService


class DiagnosisDataCollector:
    """诊断数据收集器"""

    def __init__(self, db, search_service: SearchService):
        self.db = db
        self.search_service = search_service

    async def collect_from_api_server(
        self,
        resource_type: str,
        resource_name: str,
        namespace: Optional[str],
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        从 API Server 获取资源状态和配置
        
        Args:
            resource_type: 资源类型（pods, nodes, deployments, services 等）
            resource_name: 资源名称
            namespace: 命名空间（Node 不需要）
            cluster: 集群配置
            runtime: 运行时配置
            
        Returns:
            包含 spec, status, metadata 的字典
        """
        try:
            snapshot_service = ResourceSnapshotService(self.db)
            sync_service = KubernetesResourceSyncService(cluster, snapshot_service, runtime)
            resource_detail = await sync_service.fetch_resource_detail(
                resource_type, namespace, resource_name
            )
            return {
                "spec": resource_detail.get("spec", {}),
                "status": resource_detail.get("status", {}),
                "metadata": resource_detail.get("metadata", {}),
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to fetch resource detail from API Server: %s", exc)
            return {}

    async def collect_metrics(
        self,
        resource_type: str,
        resource_name: str,
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
        namespace: Optional[str],
        time_range_hours: float = 0.5,
    ) -> Dict[str, Any]:
        """
        收集指标数据（根据资源类型选择不同的指标模板）
        
        Args:
            resource_type: 资源类型（pods, nodes, deployments, services 等）
            resource_name: 资源名称
            cluster: 集群配置
            runtime: 运行时配置
            namespace: 命名空间
            time_range_hours: 时间范围（小时），默认 0.5 小时（30分钟），深度诊断时可传入 2-4 小时
        """
        # 检查监控系统是否配置（与 PrometheusMetricsService 逻辑一致）
        # 注意：PrometheusMetricsService 的检查顺序是：runtime.get("prometheus_url") or cluster.prometheus_url
        # 所以这里也应该保持一致
        prometheus_url = runtime.get("prometheus_url") or cluster.prometheus_url
        prometheus_configured = bool(prometheus_url)
        logger.warning(
            f"[指标收集] 检查监控系统配置: 已配置={prometheus_configured}, "
            f"Prometheus URL={prometheus_url or 'N/A'}, "
            f"cluster.prometheus_url={cluster.prometheus_url or 'N/A'}, "
            f"runtime.prometheus_url={runtime.get('prometheus_url') or 'N/A'}"
        )
        if not prometheus_configured:
            logger.warning(f"[指标收集] 监控系统未配置，直接返回空结果")
            return {
                "monitoring_configured": False,
                "message": "监控系统未配置（未设置 Prometheus URL）"
            }
        
        # 创建 PrometheusMetricsService（会再次验证 URL，如果无效会抛出异常）
        try:
            service = PrometheusMetricsService(cluster, runtime)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"[指标收集] 创建 PrometheusMetricsService 失败: {exc}", exc_info=True)
            return {
                "monitoring_configured": False,
                "message": f"监控系统配置无效: {str(exc)}"
            }
        end = datetime.utcnow()
        start = end - timedelta(hours=time_range_hours)
        ns = namespace or "default"
        
        # 根据资源类型选择指标模板
        templates = []
        context: Dict[str, Any] = {"namespace": ns, "window": "5m"}
        
        if resource_type == "pods":
            templates = ["pod_cpu_usage", "pod_memory_usage", "pod_restart_rate"]
            context["pod"] = resource_name
        elif resource_type == "nodes":
            templates = ["node_cpu_usage", "node_memory_usage", "node_disk_usage"]
            context["node"] = resource_name
        elif resource_type == "services":
            templates = ["service_connection_count"]  # Endpoints 数量从 API Server 获取
            context["service"] = resource_name
        elif resource_type in ["deployments", "statefulsets", "daemonsets"]:
            templates = ["deployment_replica_count"]  # 当前副本状态从 API Server 获取
            context["deployment"] = resource_name
        else:
            # 其他资源类型暂不支持指标收集
            logger.debug("Metrics collection not supported for resource type: %s", resource_type)
            return {
                "monitoring_configured": True,
                "message": f"资源类型 {resource_type} 不支持指标收集"
            }
        
        metrics_payload: Dict[str, Any] = {
            "monitoring_configured": True,
            "time_range": {
                "start": start.isoformat() + "Z",
                "end": end.isoformat() + "Z",
                "hours": time_range_hours,
            }
        }
        # 根据时间范围调整步长
        if time_range_hours <= 1:
            step = timedelta(minutes=1)
        elif time_range_hours <= 4:
            step = timedelta(minutes=5)
        else:
            step = timedelta(minutes=15)
        
        # 统计查询状态
        success_count = 0
        error_templates: List[str] = []
        empty_templates: List[str] = []
        
        logger.warning(
            f"[指标收集] 开始收集 {resource_type}/{resource_name} 的指标数据, "
            f"时间范围={start.isoformat()} ~ {end.isoformat()}, "
            f"模板={', '.join(templates)}, 上下文={context}"
        )
        
        for template in templates:
            try:
                result = await service.run_template(template, context, start=start, end=end, step=step)
                metrics_payload[template] = result
                success_count += 1
                
                # 详细打印查询结果
                if isinstance(result, dict):
                    status = result.get("status", "unknown")
                    data = result.get("data", {})
                    results = data.get("result") if isinstance(data, dict) else None
                    
                    if isinstance(results, list):
                        result_count = len(results)
                        if result_count == 0:
                            empty_templates.append(template)
                            logger.warning(f"[指标收集结果] 模板={template}, status={status}, 结果数量=0 (空结果)")
                        else:
                            # 打印第一个结果的结构（截断内容）
                            first_result = results[0] if results else {}
                            values_count = 0
                            if "values" in first_result:
                                values = first_result.get("values", [])
                                values_count = len(values)
                            elif "value" in first_result:
                                values_count = 1
                                value = first_result.get("value", [])
                                if len(value) >= 2:
                                    logger.warning(f"[指标收集结果] 模板={template}, status={status}, 结果数量={result_count}, 当前值={value[1]}")
                                    continue
                            
                            logger.warning(
                                f"[指标收集结果] 模板={template}, status={status}, 结果数量={result_count}, "
                                f"时间序列点数量={values_count}"
                            )
                    else:
                        logger.warning(f"[指标收集] 模板 {template} 返回的 result 不是列表: {type(results)}")
                else:
                    logger.warning(f"[指标收集] 模板 {template} 返回的不是字典: {type(result)}")
                    
            except Exception as exc:  # pylint: disable=broad-except
                # 提取更友好的错误信息
                error_msg = str(exc)
                if "502 Bad Gateway" in error_msg:
                    error_msg = "Prometheus 服务暂时不可用 (502 Bad Gateway)"
                elif "503" in error_msg or "504" in error_msg:
                    error_msg = f"Prometheus 服务暂时不可用 ({exc.response.status_code if hasattr(exc, 'response') else '503/504'})"
                elif "Connection" in error_msg or "connect" in error_msg.lower():
                    error_msg = "无法连接到 Prometheus 服务"
                
                logger.warning(
                    f"[指标收集] 模板 {template} 查询失败: {error_msg}"
                )
                error_templates.append(f"{template}({error_msg[:50]})")
        
        if error_templates:
            metrics_payload["message"] = f"部分指标查询失败：{'; '.join(error_templates)}"
            logger.warning(f"[指标收集] 部分查询失败: {error_templates}")
        elif empty_templates and len(empty_templates) == len(templates):
            metrics_payload["message"] = (
                "监控系统已配置，但本次查询结果为空（可能是时间范围无数据或指标无采样）。"
                f" 空结果指标：{', '.join(empty_templates)}"
            )
            logger.warning(f"[指标收集] 所有指标查询结果为空: {empty_templates}")
        elif empty_templates:
            metrics_payload["message"] = f"成功获取 {success_count}/{len(templates)} 个指标数据，其中 {', '.join(empty_templates)} 无数据"
            logger.info(f"[指标收集] 部分指标无数据: {empty_templates}")
        else:
            metrics_payload["message"] = f"成功获取 {success_count}/{len(templates)} 个指标数据"
            logger.info(f"[指标收集] 所有指标查询成功")
        
        logger.info(f"[指标收集] 最终结果摘要: {metrics_payload.get('message', 'N/A')}")
        return metrics_payload

    async def collect_logs(
        self,
        resource_type: str,
        resource_name: str,
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
        namespace: Optional[str],
        time_range_hours: float = 0.25,
    ) -> Dict[str, Any]:
        """
        收集日志数据（根据资源类型选择不同的日志源）
        
        Args:
            resource_type: 资源类型（pods, nodes, deployments, services 等）
            resource_name: 资源名称
            cluster: 集群配置
            runtime: 运行时配置
            namespace: 命名空间
            time_range_hours: 时间范围（小时），默认 0.25 小时（15分钟），深度诊断时可传入 2-4 小时
        """
        ns = namespace or "default"
        result: Dict[str, Any] = {
            "source": None,
            "logs": [],
            "error": None,
            "log_available": False,  # 是否可以从 K8s API 获取日志
            "log_system_configured": False,  # 日志系统是否配置
            "time_range": {
                "hours": time_range_hours,
            },
        }
        
        logger.info(f"[日志收集] 开始收集 {resource_type}/{resource_name} 的日志数据，命名空间: {ns}, 时间范围: {time_range_hours} 小时")
        
        # Pod 日志：混合策略（优先 K8s API，回退到日志系统）
        if resource_type == "pods":
            # 步骤1: 尝试获取 Pod 状态，判断是否应该从 K8s API 获取日志
            pod_phase = None
            try:
                snapshot_service = ResourceSnapshotService(self.db)
                sync_service = KubernetesResourceSyncService(cluster, snapshot_service, runtime)
                pod_detail = await sync_service.fetch_resource_detail("pods", ns, resource_name)
                pod_status = pod_detail.get("status", {})
                pod_phase = pod_status.get("phase", "").lower()
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Failed to fetch pod status: %s", exc)
            
            logger.info(f"[日志收集] Pod {ns}/{resource_name} 状态: {pod_phase or 'unknown'}")
            
            # 步骤2: 如果 Pod 正在运行且时间范围较短，优先尝试从 K8s API Server 获取实时日志
            if pod_phase == "running":
                try:
                    sync_service = KubernetesResourceSyncService(
                        cluster, ResourceSnapshotService(self.db), runtime
                    )
                    
                    # 获取 Pod 详情，检查容器列表
                    pod_detail = await sync_service.fetch_resource_detail("pods", ns, resource_name)
                    pod_spec = pod_detail.get("spec", {})
                    containers = pod_spec.get("containers", [])
                    container_names = [c.get("name") for c in containers if c.get("name")]
                    
                    logger.warning(
                        f"[日志收集] Pod {ns}/{resource_name} 容器列表: {container_names}, "
                        f"容器数量: {len(container_names)}"
                    )
                    
                    # 回退策略：先尝试时间范围查询，如果为空则回退到 tailLines 获取最近日志
                    # 策略1：首先尝试使用 since_seconds 获取时间范围内的日志
                    since_seconds = int(time_range_hours * 3600) if time_range_hours <= 4.0 else None
                    initial_tail_lines = settings.OBSERVABILITY_LOG_INITIAL_TAIL_LINES
                    fallback_tail_lines = settings.OBSERVABILITY_LOG_FALLBACK_TAIL_LINES
                    max_log_lines = settings.OBSERVABILITY_LOG_MAX_LINES
                    
                    logger.warning(
                        f"[日志收集] 运行中的 Pod，首先尝试获取时间范围内的日志: "
                        f"since_seconds={since_seconds or 'None'}, tail_lines={initial_tail_lines}"
                    )
                    
                    all_log_lines = []
                    
                    # 定义一个辅助函数：获取单个容器的日志（带回退策略）
                    async def fetch_container_logs_with_fallback(
                        container_name: Optional[str],
                    ) -> List[str]:
                        """获取容器日志，如果时间范围内为空，则回退到 tailLines 获取最近日志"""
                        try:
                            # 第一次尝试：使用时间范围查询
                            log_text = await sync_service.fetch_pod_logs(
                                namespace=ns,
                                pod_name=resource_name,
                                container=container_name,
                                tail_lines=initial_tail_lines,
                                since_seconds=since_seconds,
                            )
                            
                            if log_text and log_text.strip():
                                log_lines = log_text.strip().split("\n")
                                log_lines = [line for line in log_lines if line.strip()]
                                if log_lines:
                                    logger.warning(
                                        f"[日志收集] 容器 '{container_name or '默认'}' 时间范围内有日志: "
                                        f"{len(log_lines)} 行"
                                    )
                                    return log_lines
                            
                            # 回退策略：时间范围内无日志，使用 tailLines 获取最近日志
                            logger.warning(
                                f"[日志收集] 容器 '{container_name or '默认'}' 时间范围内无日志，"
                                f"回退到 tailLines={fallback_tail_lines} 获取最近日志"
                            )
                            fallback_log_text = await sync_service.fetch_pod_logs(
                                namespace=ns,
                                pod_name=resource_name,
                                container=container_name,
                                tail_lines=fallback_tail_lines,
                                since_seconds=None,  # 不限制时间范围
                            )
                            
                            if fallback_log_text and fallback_log_text.strip():
                                fallback_log_lines = fallback_log_text.strip().split("\n")
                                fallback_log_lines = [line for line in fallback_log_lines if line.strip()]
                                if fallback_log_lines:
                                    logger.warning(
                                        f"[日志收集] 容器 '{container_name or '默认'}' 获取到最近日志: "
                                        f"{len(fallback_log_lines)} 行"
                                    )
                                    return fallback_log_lines
                            
                            logger.warning(
                                f"[日志收集] 容器 '{container_name or '默认'}' 无日志"
                            )
                            return []
                            
                        except Exception as exc:  # pylint: disable=broad-except
                            logger.warning(
                                f"[日志收集] 获取容器 '{container_name or '默认'}' 日志失败: {exc}"
                            )
                            return []
                    
                    # 如果是多容器 Pod，需要分别获取每个容器的日志
                    if len(container_names) > 1:
                        logger.warning(f"[日志收集] 多容器 Pod，分别获取 {len(container_names)} 个容器的日志")
                        for container_name in container_names:
                            container_log_lines = await fetch_container_logs_with_fallback(
                                container_name
                            )
                            # 为每行日志添加容器名称前缀
                            for line in container_log_lines:
                                all_log_lines.append(f"[{container_name}] {line}")
                    else:
                        # 单容器 Pod，明确指定容器名称获取日志
                        container_name = container_names[0] if container_names else None
                        all_log_lines = await fetch_container_logs_with_fallback(container_name)
                    
                    # 将文本日志转换为结构化格式
                    entries = []
                    
                    # 优先提取 ERROR、WARNING、FATAL 级别的日志（带上下文和大小保护）
                    def is_error_log_line(line: str) -> bool:
                        """
                        更智能的错误日志识别
                        避免误匹配（如包含 ERROR 的正常消息）
                        
                        Args:
                            line: 日志行内容
                        
                        Returns:
                            是否为错误/警告日志
                        """
                        if not line or not line.strip():
                            return False
                        
                        line_upper = line.upper()
                        
                        # 定义日志级别关键词和常见误匹配模式
                        # 优先级关键词（常见格式）
                        priority_patterns = [
                            ' ERROR ',  # 空格包围，避免匹配 "ERRORS" 等
                            ' ERROR:',  # 冒号格式
                            ' ERROR]',  # 方括号格式
                            '[ERROR',   # 方括号格式（开头）
                            ' WARNING ',  # 空格包围
                            ' WARNING:',  # 冒号格式
                            ' WARNING]',  # 方括号格式
                            '[WARNING',   # 方括号格式
                            ' WARN ',     # 空格包围
                            ' WARN:',     # 冒号格式
                            ' WARN]',     # 方括号格式
                            '[WARN',      # 方括号格式
                            ' FATAL ',    # 空格包围
                            ' FATAL:',    # 冒号格式
                            ' FATAL]',    # 方括号格式
                            '[FATAL',     # 方括号格式
                            ' CRITICAL ', # 空格包围
                            ' CRITICAL:', # 冒号格式
                            ' CRITICAL]', # 方括号格式
                            '[CRITICAL',  # 方括号格式
                            'EXCEPTION',  # 异常信息
                            'EXCEPTION:', # 异常信息带冒号
                            'EXCEPTION]', # 异常信息带方括号
                            '[EXCEPTION', # 异常信息带方括号开头
                        ]
                        
                        # 排除误匹配模式（包含这些关键词但不是错误日志）
                        false_positive_patterns = [
                            'NO ERROR',      # 无错误
                            'NO WARNING',    # 无警告
                            'NO EXCEPTION',  # 无异常
                            'IGNORED ERROR', # 忽略的错误
                        ]
                        
                        # 检查是否为误匹配
                        for pattern in false_positive_patterns:
                            if pattern in line_upper:
                                return False
                        
                        # 检查是否匹配错误日志模式
                        for pattern in priority_patterns:
                            if pattern in line_upper:
                                return True
                        
                        # 检查行首或行尾的特殊格式（如 "ERROR - " 或 " - ERROR"）
                        if line_upper.startswith('ERROR') or line_upper.startswith('WARNING') or \
                           line_upper.startswith('FATAL') or line_upper.startswith('CRITICAL'):
                            return True
                        
                        # 检查常见的 Java/Spring 错误格式
                        if any(pattern in line_upper for pattern in [
                            '.ERROR',
                            '.WARN',
                            '.FATAL',
                            'java.lang.',
                            'java.net.',
                            'java.io.',
                            'Exception in thread',
                            'Caused by:',
                        ]):
                            return True
                        
                        return False
                    
                    def truncate_log_line(line: str, max_length: int) -> str:
                        """
                        截断过长的日志行
                        
                        Args:
                            line: 日志行内容
                            max_length: 最大长度
                        
                        Returns:
                            截断后的日志行（如果超长，会添加截断标记）
                        """
                        if not line:
                            return line
                        
                        if len(line) <= max_length:
                            return line
                        
                        # 保留前 90% 的内容，后 10% 用于截断标记
                        truncate_at = int(max_length * 0.9)
                        truncated = line[:truncate_at]
                        remaining = len(line) - truncate_at
                        return f"{truncated}... [TRUNCATED {remaining} chars]"
                    
                    def prioritize_logs_with_context(
                        log_lines: List[str], 
                        max_lines: int, 
                        context_lines: int = 3
                    ) -> List[str]:
                        """
                        优先提取包含 ERROR、WARNING、FATAL 的日志行及其上下文
                        保持原始时间顺序，确保关键错误信息不被截断
                        同时保护日志大小（截断过长日志）
                        
                        Args:
                            log_lines: 原始日志行列表（按时间顺序）
                            max_lines: 最大返回行数
                            context_lines: 错误日志上下文行数（前后各几行）
                        
                        Returns:
                            处理后的日志行列表（优先级：ERROR/WARNING/FATAL + 上下文 > 其他）
                        """
                        if not log_lines:
                            return []
                        
                        # 首先截断过长的日志行
                        max_line_length = settings.OBSERVABILITY_LOG_MAX_LINE_LENGTH
                        truncated_log_lines = [truncate_log_line(line, max_line_length) for line in log_lines]
                        
                        if len(truncated_log_lines) <= max_lines:
                            return truncated_log_lines
                        
                        # 标记每行是否为优先级日志
                        log_with_flags = []
                        priority_indices = set()
                        
                        for idx, line in enumerate(truncated_log_lines):
                            is_priority = is_error_log_line(line)
                            log_with_flags.append((idx, line, is_priority))
                            if is_priority:
                                priority_indices.add(idx)
                        
                        # 如果没有优先级日志，直接返回最近的日志
                        if not priority_indices:
                            return truncated_log_lines[-max_lines:]
                        
                        # 收集优先级日志及其上下文
                        selected_indices = set()
                        
                        for priority_idx in priority_indices:
                            # 添加优先级日志本身
                            selected_indices.add(priority_idx)
                            
                            # 添加上下文（前面的日志）
                            for i in range(max(0, priority_idx - context_lines), priority_idx):
                                selected_indices.add(i)
                            
                            # 添加上下文（后面的日志）
                            max_idx = len(truncated_log_lines) - 1
                            for i in range(priority_idx + 1, min(max_idx + 1, priority_idx + context_lines + 1)):
                                selected_indices.add(i)
                        
                        # 如果选中的日志数量已超过限制，优先保留优先级日志
                        if len(selected_indices) > max_lines:
                            # 先保留所有优先级日志
                            result_indices = set(priority_indices)
                            
                            # 计算剩余槽位
                            remaining_slots = max_lines - len(result_indices)
                            
                            # 优先保留优先级日志的直接上下文
                            context_indices = selected_indices - priority_indices
                            if len(context_indices) > remaining_slots:
                                # 从优先级日志的上下文中选择（按距离优先级日志的远近）
                                context_with_distance = []
                                for ctx_idx in context_indices:
                                    # 计算到最近优先级日志的距离
                                    min_distance = min(abs(ctx_idx - pri_idx) for pri_idx in priority_indices)
                                    context_with_distance.append((ctx_idx, min_distance))
                                
                                # 按距离排序，优先保留距离近的上下文
                                context_with_distance.sort(key=lambda x: x[1])
                                for ctx_idx, _ in context_with_distance[:remaining_slots]:
                                    result_indices.add(ctx_idx)
                            else:
                                result_indices.update(context_indices)
                            
                            selected_indices = result_indices
                        
                        # 如果选中的日志数量仍然不足，补充最近的日志
                        if len(selected_indices) < max_lines:
                            remaining_slots = max_lines - len(selected_indices)
                            other_indices = [idx for idx in range(len(truncated_log_lines)) if idx not in selected_indices]
                            
                            if other_indices:
                                # 从后往前取最近的日志
                                other_indices_to_add = other_indices[-remaining_slots:] if len(other_indices) > remaining_slots else other_indices
                                selected_indices.update(other_indices_to_add)
                        
                        # 按原始索引顺序返回，保持时间顺序
                        result = []
                        for idx, line, _ in log_with_flags:
                            if idx in selected_indices:
                                result.append(line)
                                if len(result) >= max_lines:
                                    break
                        
                        return result
                    
                    # 使用改进的优先级排序处理日志（带上下文和大小保护）
                    context_lines = settings.OBSERVABILITY_LOG_CONTEXT_LINES
                    log_lines_to_process = prioritize_logs_with_context(
                        all_log_lines, 
                        max_log_lines, 
                        context_lines=context_lines
                    )
                    
                    # 统计优先级日志数量（使用改进的错误日志识别函数）
                    priority_count = sum(1 for line in log_lines_to_process if is_error_log_line(line))
                    truncated_count = sum(1 for line in log_lines_to_process if '[TRUNCATED' in line)
                    
                    logger.warning(
                        f"[日志收集] 原始日志行数: {len(all_log_lines)}, "
                        f"处理后返回行数: {len(log_lines_to_process)} (最大限制: {max_log_lines}), "
                        f"优先级日志(ERROR/WARNING/FATAL): {priority_count} 条, "
                        f"截断日志: {truncated_count} 条, "
                        f"上下文行数: {context_lines}"
                    )
                    
                    for line in log_lines_to_process:
                        if line.strip():
                            entries.append({
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "message": line,
                                "source": "k8s_api",
                            })
                    
                    result.update({
                        "source": "k8s_api",
                        "logs": entries,
                        "total": len(entries),
                        "log_available": True,  # 可以从 K8s API 获取
                    })
                    logger.warning(
                        f"[日志收集] 成功从 K8s API 获取 Pod {ns}/{resource_name} 的日志: "
                        f"共 {len(entries)} 条，原始日志行数: {len(all_log_lines)}, "
                        f"容器数量: {len(container_names)}"
                    )
                    if entries:
                        logger.debug(f"[日志收集] 前3条日志示例: {[e.get('message', '')[:100] for e in entries[:3]]}")
                    else:
                        logger.warning(
                            f"[日志收集] Pod {ns}/{resource_name} 日志为空，"
                            f"容器列表: {container_names}, "
                            f"原始日志行数: {len(all_log_lines)}"
                        )
                    return result
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning(f"[日志收集] 从 K8s API 获取 Pod {ns}/{resource_name} 日志失败，回退到日志系统: {exc}", exc_info=True)
                    result["error"] = f"K8s API failed: {str(exc)}"
            else:
                logger.info(f"[日志收集] Pod {ns}/{resource_name} 不在运行状态（phase={pod_phase}），尝试使用日志系统")
            
            # 步骤3: 回退到日志系统（Pod 不在运行状态或 K8s API 失败）
            log_system_configured = bool(cluster.log_endpoint or runtime.get("log_endpoint"))
            result["log_system_configured"] = log_system_configured
            if not log_system_configured:
                # Pod 不在运行状态且日志系统未配置，但可以通过 K8s API 获取（虽然已失败）
                logger.warning(
                    f"[日志收集] Pod {ns}/{resource_name} 不在运行状态且日志系统未配置。"
                    f"注意：运行中的 Pod 可以通过 K8s API 获取日志，无需日志系统。"
                )
                result["error"] = "Pod 不在运行状态，且日志系统未配置。注意：运行中的 Pod 可以通过 K8s API 获取日志，无需日志系统。"
                return result
            
            try:
                logs_service = LogQueryService(cluster, runtime)
                query = resource_name
                system = (runtime.get("log_system") or cluster.log_system or "").lower()
                logger.info(f"[日志收集] 使用日志系统: {system}, Pod: {ns}/{resource_name}")
                if system == "loki":
                    # Loki 需要合法的 logQL 表达式
                    selector = f'{{namespace="{ns}", pod="{resource_name}"}}'
                    query = f'{selector} |= ""'
                    logger.debug(f"[日志收集] Loki 查询语句: {query}")
                
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=time_range_hours)
                # 日志系统查询时，获取更多日志以便后续过滤和排序
                # 最终会通过 max_log_lines 限制返回的行数
                max_log_lines = settings.OBSERVABILITY_LOG_MAX_LINES
                log_limit = (max_log_lines * 2) if time_range_hours > 1.0 else max_log_lines
                log_result = await logs_service.query_logs(
                    query, start=start_time, end=end_time, limit=log_limit
                )
                
                # 转换日志系统返回的格式
                entries = log_result.get("results", [])
                total = log_result.get("pagination", {}).get("total", len(entries))
                
                # 定义辅助函数：处理日志系统返回的日志（带上下文和大小保护）
                def filter_log_system_entries(log_entries: List[Dict], max_lines: int) -> List[Dict]:
                    """对日志系统返回的日志应用优先级过滤、上下文提取和大小保护"""
                    if len(log_entries) <= max_lines:
                        # 即使不超过限制，也要截断过长的日志行
                        max_line_length = settings.OBSERVABILITY_LOG_MAX_LINE_LENGTH
                        for entry in log_entries:
                            msg = entry.get("message") or entry.get("log") or str(entry)
                            if isinstance(msg, dict):
                                msg = str(msg)
                            if len(str(msg)) > max_line_length:
                                truncate_at = int(max_line_length * 0.9)
                                truncated = str(msg)[:truncate_at]
                                remaining = len(str(msg)) - truncate_at
                                entry["message"] = f"{truncated}... [TRUNCATED {remaining} chars]"
                        return log_entries
                    
                    # 提取日志消息内容
                    log_messages = []
                    for entry in log_entries:
                        message = entry.get("message") or entry.get("log") or str(entry)
                        if isinstance(message, dict):
                            message = str(message)
                        # 截断过长的日志行
                        max_line_length = settings.OBSERVABILITY_LOG_MAX_LINE_LENGTH
                        if len(message) > max_line_length:
                            truncate_at = int(max_line_length * 0.9)
                            truncated = message[:truncate_at]
                            remaining = len(message) - truncate_at
                            message = f"{truncated}... [TRUNCATED {remaining} chars]"
                        log_messages.append(message)
                    
                    # 使用改进的错误日志识别逻辑（与 is_error_log_line 保持一致）
                    def is_error_entry(msg: str) -> bool:
                        if not msg or not str(msg).strip():
                            return False
                        msg_upper = str(msg).upper()
                        
                        # 排除误匹配
                        if any(pattern in msg_upper for pattern in ['NO ERROR', 'NO WARNING', 'NO EXCEPTION', 'IGNORED ERROR']):
                            return False
                        
                        # 检查优先级模式
                        priority_patterns = [
                            ' ERROR ', ' ERROR:', ' ERROR]', '[ERROR',
                            ' WARNING ', ' WARNING:', ' WARNING]', '[WARNING',
                            ' WARN ', ' WARN:', ' WARN]', '[WARN',
                            ' FATAL ', ' FATAL:', ' FATAL]', '[FATAL',
                            ' CRITICAL ', ' CRITICAL:', ' CRITICAL]', '[CRITICAL',
                            'EXCEPTION', 'EXCEPTION:', 'EXCEPTION]', '[EXCEPTION',
                        ]
                        if any(pattern in msg_upper for pattern in priority_patterns):
                            return True
                        
                        if msg_upper.startswith(('ERROR', 'WARNING', 'FATAL', 'CRITICAL')):
                            return True
                        
                        if any(pattern in msg_upper for pattern in [
                            '.ERROR', '.WARN', '.FATAL',
                            'java.lang.', 'java.net.', 'java.io.',
                            'Exception in thread', 'Caused by:',
                        ]):
                            return True
                        
                        return False
                    
                    # 标记优先级日志
                    priority_indices = set()
                    for idx, msg in enumerate(log_messages):
                        if is_error_entry(msg):
                            priority_indices.add(idx)
                    
                    # 如果没有优先级日志，直接返回最近的日志
                    if not priority_indices:
                        return log_entries[-max_lines:]
                    
                    # 收集优先级日志及其上下文
                    context_lines = settings.OBSERVABILITY_LOG_CONTEXT_LINES
                    selected_indices = set()
                    
                    for priority_idx in priority_indices:
                        selected_indices.add(priority_idx)
                        # 添加上下文
                        for i in range(max(0, priority_idx - context_lines), priority_idx):
                            selected_indices.add(i)
                        for i in range(priority_idx + 1, min(len(log_entries), priority_idx + context_lines + 1)):
                            selected_indices.add(i)
                    
                    # 如果超过限制，优先保留优先级日志和近的上下文
                    if len(selected_indices) > max_lines:
                        result_indices = set(priority_indices)
                        remaining_slots = max_lines - len(result_indices)
                        context_indices = selected_indices - priority_indices
                        
                        if len(context_indices) > remaining_slots:
                            # 按距离排序，优先保留距离近的上下文
                            context_with_distance = [
                                (ctx_idx, min(abs(ctx_idx - pri_idx) for pri_idx in priority_indices))
                                for ctx_idx in context_indices
                            ]
                            context_with_distance.sort(key=lambda x: x[1])
                            for ctx_idx, _ in context_with_distance[:remaining_slots]:
                                result_indices.add(ctx_idx)
                        else:
                            result_indices.update(context_indices)
                        
                        selected_indices = result_indices
                    
                    # 如果仍然不足，补充最近的日志
                    if len(selected_indices) < max_lines:
                        remaining_slots = max_lines - len(selected_indices)
                        other_indices = [idx for idx in range(len(log_entries)) if idx not in selected_indices]
                        if other_indices:
                            selected_indices.update(other_indices[-remaining_slots:] if len(other_indices) > remaining_slots else other_indices)
                    
                    # 按原始顺序返回，并更新消息内容
                    result = []
                    for idx in sorted(selected_indices):
                        if idx < len(log_entries):
                            entry = log_entries[idx].copy()
                            entry["message"] = log_messages[idx]
                            result.append(entry)
                    
                    return result[:max_lines]
                
                # 应用过滤和大小保护
                entries = filter_log_system_entries(entries, max_log_lines)
                
                result.update({
                    "source": "log_system",
                    "logs": entries,
                    "total": total,
                    "raw": log_result,
                })
                priority_count = sum(1 for e in entries if any(kw in str(e.get("message", e.get("log", ""))).upper() 
                                                               for kw in ['ERROR', 'WARNING', 'WARN', 'FATAL', 'CRITICAL', 'EXCEPTION']))
                logger.info(
                    f"[日志收集] 成功从日志系统获取 Pod {ns}/{resource_name} 的日志: "
                    f"共 {len(entries)} 条（总数: {total}），优先级日志: {priority_count} 条，查询语句: {query}"
                )
                if entries:
                    logger.debug(f"[日志收集] 前3条日志示例: {[e.get('message', e.get('log', ''))[:100] for e in entries[:3]]}")
                return result
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(f"[日志收集] 从日志系统获取 Pod {ns}/{resource_name} 日志失败: {exc}", exc_info=True)
                result["error"] = f"Log system failed: {str(exc)}"
                logger.error(f"[日志收集] Pod {ns}/{resource_name} 日志收集最终失败: {result.get('error')}")
                return result
        
        # Node、Service 等其他资源类型的日志：只能通过日志系统获取
        elif resource_type in ["nodes", "services"]:
            log_system_configured = bool(cluster.log_endpoint or runtime.get("log_endpoint"))
            result["log_system_configured"] = log_system_configured
            logger.info(f"[日志收集] {resource_type} {ns}/{resource_name} 日志系统配置状态: {log_system_configured}")
            if not log_system_configured:
                logger.warning(
                    f"[日志收集] {resource_type} {ns}/{resource_name} 日志系统未配置。"
                    f"注意：Pod 日志可以通过 K8s API 获取，但 Node/Service 日志需要日志系统。"
                )
                result["error"] = "日志系统未配置（未设置日志系统端点）。注意：Pod 日志可以通过 K8s API 获取，但 Node/Service 日志需要日志系统。"
                return result
            
            try:
                logs_service = LogQueryService(cluster, runtime)
                system = (runtime.get("log_system") or cluster.log_system or "").lower()
                logger.info(f"[日志收集] 使用日志系统: {system}, {resource_type}: {ns}/{resource_name}")
                
                if resource_type == "nodes":
                    # Node 日志：Kubelet 日志、系统日志
                    if system == "loki":
                        selector = f'{{node="{resource_name}"}}'
                        query = f'{selector} |= ""'
                    else:
                        query = f"node:{resource_name}"
                elif resource_type == "services":
                    # Service 日志：网络连接日志、代理日志
                    if system == "loki":
                        selector = f'{{namespace="{ns}", service="{resource_name}"}}'
                        query = f'{selector} |= ""'
                    else:
                        query = f"service:{resource_name} namespace:{ns}"
                logger.debug(f"[日志收集] {resource_type} 查询语句: {query}")
                
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=time_range_hours)
                # 日志系统查询时，获取更多日志以便后续过滤和排序
                # 最终会通过 max_log_lines 限制返回的行数
                max_log_lines = settings.OBSERVABILITY_LOG_MAX_LINES
                log_limit = (max_log_lines * 2) if time_range_hours > 1.0 else max_log_lines
                log_result = await logs_service.query_logs(
                    query, start=start_time, end=end_time, limit=log_limit
                )
                
                entries = log_result.get("results", [])
                total = log_result.get("pagination", {}).get("total", len(entries))
                
                # 复用 Pod 日志的过滤逻辑（使用相同的 filter_log_system_entries 逻辑）
                # 定义辅助函数：处理日志系统返回的日志（带上下文和大小保护）
                def filter_log_system_entries_for_node_service(log_entries: List[Dict], max_lines: int) -> List[Dict]:
                    """对日志系统返回的日志应用优先级过滤、上下文提取和大小保护（Node/Service专用）"""
                    if len(log_entries) <= max_lines:
                        # 即使不超过限制，也要截断过长的日志行
                        max_line_length = settings.OBSERVABILITY_LOG_MAX_LINE_LENGTH
                        for entry in log_entries:
                            msg = entry.get("message") or entry.get("log") or str(entry)
                            if isinstance(msg, dict):
                                msg = str(msg)
                            if len(str(msg)) > max_line_length:
                                truncate_at = int(max_line_length * 0.9)
                                truncated = str(msg)[:truncate_at]
                                remaining = len(str(msg)) - truncate_at
                                entry["message"] = f"{truncated}... [TRUNCATED {remaining} chars]"
                        return log_entries
                    
                    # 提取日志消息内容
                    log_messages = []
                    for entry in log_entries:
                        message = entry.get("message") or entry.get("log") or str(entry)
                        if isinstance(message, dict):
                            message = str(message)
                        # 截断过长的日志行
                        max_line_length = settings.OBSERVABILITY_LOG_MAX_LINE_LENGTH
                        if len(message) > max_line_length:
                            truncate_at = int(max_line_length * 0.9)
                            truncated = message[:truncate_at]
                            remaining = len(message) - truncate_at
                            message = f"{truncated}... [TRUNCATED {remaining} chars]"
                        log_messages.append(message)
                    
                    # 使用改进的错误日志识别逻辑
                    def is_error_entry(msg: str) -> bool:
                        if not msg or not str(msg).strip():
                            return False
                        msg_upper = str(msg).upper()
                        
                        # 排除误匹配
                        if any(pattern in msg_upper for pattern in ['NO ERROR', 'NO WARNING', 'NO EXCEPTION', 'IGNORED ERROR']):
                            return False
                        
                        # 检查优先级模式
                        priority_patterns = [
                            ' ERROR ', ' ERROR:', ' ERROR]', '[ERROR',
                            ' WARNING ', ' WARNING:', ' WARNING]', '[WARNING',
                            ' WARN ', ' WARN:', ' WARN]', '[WARN',
                            ' FATAL ', ' FATAL:', ' FATAL]', '[FATAL',
                            ' CRITICAL ', ' CRITICAL:', ' CRITICAL]', '[CRITICAL',
                            'EXCEPTION', 'EXCEPTION:', 'EXCEPTION]', '[EXCEPTION',
                        ]
                        if any(pattern in msg_upper for pattern in priority_patterns):
                            return True
                        
                        if msg_upper.startswith(('ERROR', 'WARNING', 'FATAL', 'CRITICAL')):
                            return True
                        
                        if any(pattern in msg_upper for pattern in [
                            '.ERROR', '.WARN', '.FATAL',
                            'java.lang.', 'java.net.', 'java.io.',
                            'Exception in thread', 'Caused by:',
                        ]):
                            return True
                        
                        return False
                    
                    # 标记优先级日志
                    priority_indices = set()
                    for idx, msg in enumerate(log_messages):
                        if is_error_entry(msg):
                            priority_indices.add(idx)
                    
                    # 如果没有优先级日志，直接返回最近的日志
                    if not priority_indices:
                        return log_entries[-max_lines:]
                    
                    # 收集优先级日志及其上下文
                    context_lines = settings.OBSERVABILITY_LOG_CONTEXT_LINES
                    selected_indices = set()
                    
                    for priority_idx in priority_indices:
                        selected_indices.add(priority_idx)
                        # 添加上下文
                        for i in range(max(0, priority_idx - context_lines), priority_idx):
                            selected_indices.add(i)
                        for i in range(priority_idx + 1, min(len(log_entries), priority_idx + context_lines + 1)):
                            selected_indices.add(i)
                    
                    # 如果超过限制，优先保留优先级日志和近的上下文
                    if len(selected_indices) > max_lines:
                        result_indices = set(priority_indices)
                        remaining_slots = max_lines - len(result_indices)
                        context_indices = selected_indices - priority_indices
                        
                        if len(context_indices) > remaining_slots:
                            # 按距离排序，优先保留距离近的上下文
                            context_with_distance = [
                                (ctx_idx, min(abs(ctx_idx - pri_idx) for pri_idx in priority_indices))
                                for ctx_idx in context_indices
                            ]
                            context_with_distance.sort(key=lambda x: x[1])
                            for ctx_idx, _ in context_with_distance[:remaining_slots]:
                                result_indices.add(ctx_idx)
                        else:
                            result_indices.update(context_indices)
                        
                        selected_indices = result_indices
                    
                    # 如果仍然不足，补充最近的日志
                    if len(selected_indices) < max_lines:
                        remaining_slots = max_lines - len(selected_indices)
                        other_indices = [idx for idx in range(len(log_entries)) if idx not in selected_indices]
                        if other_indices:
                            selected_indices.update(other_indices[-remaining_slots:] if len(other_indices) > remaining_slots else other_indices)
                    
                    # 按原始顺序返回，并更新消息内容
                    result = []
                    for idx in sorted(selected_indices):
                        if idx < len(log_entries):
                            entry = log_entries[idx].copy()
                            entry["message"] = log_messages[idx]
                            result.append(entry)
                    
                    return result[:max_lines]
                
                # 应用过滤和大小保护
                entries = filter_log_system_entries_for_node_service(entries, max_log_lines)
                
                result.update({
                    "source": "log_system",
                    "logs": entries,
                    "total": total,
                    "raw": log_result,
                })
                priority_count = sum(1 for e in entries if any(kw in str(e.get("message", e.get("log", ""))).upper() 
                                                               for kw in ['ERROR', 'WARNING', 'WARN', 'FATAL', 'CRITICAL', 'EXCEPTION']))
                logger.info(
                    f"[日志收集] 成功从日志系统获取 {resource_type} {ns}/{resource_name} 的日志: "
                    f"共 {len(entries)} 条（总数: {total}），优先级日志: {priority_count} 条，查询语句: {query}"
                )
                if entries:
                    logger.debug(f"[日志收集] 前3条日志示例: {[e.get('message', e.get('log', ''))[:100] for e in entries[:3]]}")
                return result
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(f"[日志收集] 从日志系统获取 {resource_type} {ns}/{resource_name} 日志失败: {exc}", exc_info=True)
                result["error"] = f"Log system failed: {str(exc)}"
                logger.error(f"[日志收集] {resource_type} {ns}/{resource_name} 日志收集最终失败: {result.get('error')}")
                return result
        
        # 其他资源类型暂不支持日志收集
        else:
            result["error"] = f"Log collection not supported for resource type: {resource_type}"
            logger.warning(f"[日志收集] 资源类型 {resource_type} 不支持日志收集")
            return result

    async def collect_data(
        self,
        resource_type: str,
        resource_name: str,
        namespace: Optional[str],
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
        time_range_hours: float = 0.5,
    ) -> Dict[str, Any]:
        """
        统一的数据收集入口
        
        Args:
            resource_type: 资源类型（pods, nodes, deployments, services 等）
            resource_name: 资源名称
            namespace: 命名空间
            cluster: 集群配置
            runtime: 运行时配置
            time_range_hours: 时间范围（小时），默认 0.5 小时
            
        Returns:
            包含 api_data, metrics, logs 的字典
        """
        logger.warning(
            f"[数据收集入口] 开始收集 {resource_type}/{resource_name} 的数据, "
            f"命名空间={namespace}, 时间范围={time_range_hours}小时"
        )
        
        # 1. 从 API Server 获取资源状态和配置
        logger.warning(f"[数据收集入口] 步骤1: 从 API Server 获取资源状态和配置")
        api_data = await self.collect_from_api_server(
            resource_type, resource_name, namespace, cluster, runtime
        )
        logger.warning(f"[数据收集入口] API Server 数据收集完成, 结果={bool(api_data)}")
        
        # 2. 从监控系统获取指标（根据资源类型选择指标模板）
        logger.warning(f"[数据收集入口] 步骤2: 从监控系统获取指标")
        metrics = await self.collect_metrics(
            resource_type, resource_name, cluster, runtime, namespace, time_range_hours
        )
        logger.warning(f"[数据收集入口] 指标收集完成, 监控配置={metrics.get('monitoring_configured', False)}, 消息={metrics.get('message', 'N/A')}")
        
        # 3. 从日志系统获取日志（根据资源类型选择日志源）
        logger.warning(f"[数据收集入口] 步骤3: 从日志系统获取日志")
        log_time_range_hours = min(time_range_hours, 0.25)  # 日志默认 15 分钟
        logs = await self.collect_logs(
            resource_type, resource_name, cluster, runtime, namespace, log_time_range_hours
        )
        logger.warning(f"[数据收集入口] 日志收集完成, 来源={logs.get('source', 'N/A')}, 数量={len(logs.get('logs', []))}")
        
        logger.warning(f"[数据收集入口] 数据收集完成, 返回结果")
        return {
            "api_data": api_data,
            "metrics": metrics,
            "logs": logs,
        }

    async def search_knowledge(self, problem_summary: str) -> Optional[List[Dict[str, Any]]]:
        """
        基于问题总结搜索知识库
        
        Args:
            problem_summary: 问题总结文本（由 LLM 生成）
        
        Returns:
            List[Dict] 包含知识库文档的详细信息，格式: [{"document_id": int, "content": str, "title": str, ...}, ...]
        """
        try:
            logger.info(f"[知识库搜索] 基于问题总结搜索: {problem_summary[:100]}...")
            # 使用现有搜索服务（OpenSearch）
            hits = await self.search_service.mixed_search(
                query_text=problem_summary,
                knowledge_base_id=None,
                top_k=5,
            )
            
            # 返回完整的文档信息，而不仅仅是 ID
            knowledge_docs = []
            for hit in hits:
                doc_id = hit.get("document_id")
                if doc_id:
                    knowledge_docs.append({
                        "document_id": doc_id,
                        "title": hit.get("title", ""),
                        "content": hit.get("content", "")[:2000],  # 限制内容长度
                        "score": hit.get("score", 0.0),
                        "metadata": hit.get("metadata", {}),
                    })
            
            logger.info(f"[知识库搜索] 找到 {len(knowledge_docs)} 个相关文档")
            return knowledge_docs if knowledge_docs else None
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(f"知识库搜索失败: {exc}", exc_info=True)
            return None

    async def search_external(self, problem_summary: str, resource_name: str, namespace: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        """
        外部搜索（Searxng）
        
        Args:
            problem_summary: 问题总结文本（用于搜索关键词）
            resource_name: 资源名称
            namespace: 命名空间
        """
        if not settings.SEARXNG_URL:
            logger.warning("[外部搜索] SEARXNG_URL 未配置，跳过外部搜索")
            return None
        # 使用扩展信息增强的问题总结作为搜索关键词（符合设计文档要求）
        query = f"{problem_summary} Kubernetes {resource_name} {namespace or ''} 排查".strip()
        url = settings.SEARXNG_URL.rstrip("/") + "/search"
        params = {"q": query, "format": "json", "categories": "it"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            results = data.get("results", [])[:5]
            formatted = [
                {"title": item.get("title"), "url": item.get("url")}
                for item in results
                if item.get("url")
            ]
            return formatted or None
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("外部搜索失败: %s", exc)
            return None
