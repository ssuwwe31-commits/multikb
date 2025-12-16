"""
Prometheus metrics querying service with template support.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx  # type: ignore

from app.core.logging import logger
from app.models.cluster_config import ClusterConfig
from app.core.cache import cache_manager
from app.config.settings import settings


DEFAULT_TEMPLATES: Dict[str, str] = {
    "pod_cpu_usage": 'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod="{pod}", container!="POD"}}[{window}]))',
    "pod_memory_usage": 'max(container_memory_usage_bytes{{namespace="{namespace}", pod="{pod}", container!="POD"}})',
    "pod_restart_rate": 'sum(rate(kube_pod_container_status_restarts_total{{namespace="{namespace}", pod="{pod}"}}[{window}]))',
    "node_cpu_total": 'sum(rate(node_cpu_seconds_total{{mode!="idle"}}[{window}])) by (instance)',
    "node_memory_usage": 'node_memory_Active_bytes',
}


class PrometheusMetricsService:
    """Service for querying Prometheus metrics."""

    def __init__(self, cluster: ClusterConfig, runtime_config: Optional[Dict[str, Any]] = None):
        from app.core.exceptions import CustomException, ErrorCode
        
        runtime = runtime_config or {}
        prometheus_url = runtime.get("prometheus_url") or cluster.prometheus_url
        if not prometheus_url:
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"集群 '{cluster.name}' 未配置 Prometheus 监控地址，请先在集群配置中添加 Prometheus URL"
            )
        self.cluster = cluster
        self.runtime = runtime
        self.base_url = prometheus_url.rstrip("/")
        self.auth_type = (runtime.get("prometheus_auth_type") or cluster.prometheus_auth_type or "none").lower()
        self.username = runtime.get("prometheus_username") or cluster.prometheus_username
        self.password = runtime.get("prometheus_password") or cluster.prometheus_password

    async def query(
        self,
        promql: str,
        time: Optional[datetime] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        params = {"query": promql}
        if time:
            params["time"] = int(time.timestamp())
        logger.debug(f"[Prometheus查询] query - PromQL: {promql}, 时间: {time.isoformat() if time else 'now'}")
        response = await self._request("/api/v1/query", params=params, timeout=timeout)
        return response

    async def query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step: timedelta,
        timeout: int = 30,  # 默认增加到 30 秒，因为 query_range 通常需要更长时间
    ) -> Dict[str, Any]:
        params = {
            "query": promql,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": int(step.total_seconds()),
        }
        logger.debug(
            f"[Prometheus查询] query_range - PromQL: {promql}, "
            f"时间: {start.isoformat()} - {end.isoformat()}, "
            f"步长: {step.total_seconds()}秒, 超时={timeout}秒"
        )
        response = await self._request("/api/v1/query_range", params=params, timeout=timeout)
        return response

    async def run_template(
        self,
        template_id: str,
        context: Dict[str, Any],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        from app.core.exceptions import CustomException, ErrorCode
        import string
        
        if template_id not in DEFAULT_TEMPLATES:
            raise ValueError(f"Unknown metrics template: {template_id}")
        
        template = DEFAULT_TEMPLATES[template_id]
        # 从模板字符串中提取需要的参数（例如 {namespace}, {pod}, {window}）
        formatter = string.Formatter()
        required_params = [field_name for _, field_name, _, _ in formatter.parse(template) if field_name]
        
        # 检查是否缺少必需参数
        missing_params = [param for param in required_params if param not in context]
        if missing_params:
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"模板 '{template_id}' 缺少必需的参数: {', '.join(missing_params)}。请确保在 context 中提供这些参数。"
            )
        
        try:
            expression = template.format(**context)
        except KeyError as e:
            missing_key = str(e).strip("'")
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"模板 '{template_id}' 缺少必需的参数: {missing_key}。请确保在 context 中提供此参数。"
            ) from e
        
        # 打印查询信息（使用 WARNING 级别确保能看到）
        logger.warning(
            f"[Prometheus查询] 模板={template_id}, PromQL={expression}, "
            f"时间范围={start.isoformat() if start else 'N/A'} ~ {end.isoformat() if end else 'N/A'}, "
            f"步长={step.total_seconds() if step else 'N/A'}秒, 上下文={context}"
        )
        
        if start and end and step:
            result = await self.query_range(expression, start, end, step)
        else:
            result = await self.query(expression)
        
        # 打印查询结果（使用 WARNING 级别确保能看到）
        if isinstance(result, dict):
            status = result.get("status", "unknown")
            data = result.get("data", {})
            result_list = data.get("result", []) if isinstance(data, dict) else []
            result_count = len(result_list) if isinstance(result_list, list) else 0
            
            if result_count == 0:
                logger.warning(
                    f"[Prometheus查询结果] 模板={template_id}, status={status}, 结果数量=0 (空结果), "
                    f"PromQL={expression}"
                )
            else:
                logger.warning(
                    f"[Prometheus查询结果] 模板={template_id}, status={status}, 结果数量={result_count}"
                )
                # 打印第一个结果的标签（用于调试）
                first_result = result_list[0] if result_list else {}
                if isinstance(first_result, dict) and "metric" in first_result:
                    metric_labels = first_result.get("metric", {})
                    logger.warning(f"[Prometheus查询结果] 第一个结果标签: {metric_labels}")
        else:
            logger.error(f"[Prometheus查询结果] 模板={template_id}, 返回类型错误: {type(result)}")
        
        return result

    async def _request(self, path: str, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        cache_key = self._build_cache_key(path, params)
        cached = await cache_manager.get(cache_key)
        if cached:
            # 打印缓存命中信息（使用 WARNING 级别确保能看到）
            status = cached.get("status", "unknown")
            data_obj = cached.get("data", {})
            result_list = data_obj.get("result", []) if isinstance(data_obj, dict) else []
            result_count = len(result_list) if isinstance(result_list, list) else 0
            logger.warning(
                f"[Prometheus缓存命中] 路径={path}, 结果数量={result_count}, PromQL={params.get('query', 'N/A')}"
            )
            if result_count == 0:
                logger.warning(f"[Prometheus缓存结果为空] 查询参数: {params}")
            return cached

        url = urljoin(self.base_url + "/", path.lstrip("/"))
        headers = {}
        if self.auth_type == "basic" and self.username and self.password:
            import base64

            token = base64.b64encode(
                f"{self.username}:{self.password}".encode("utf-8")
            ).decode("utf-8")
            headers["Authorization"] = f"Basic {token}"
        elif self.auth_type == "token" and self.password:
            headers["Authorization"] = f"Bearer {self.password}"

        # 打印完整的请求信息，方便调试
        query_preview = params.get('query', 'N/A')
        if isinstance(query_preview, str) and len(query_preview) > 100:
            query_preview = query_preview[:100] + "..."
        
        logger.warning(
            f"[Prometheus请求详情] base_url={self.base_url}, path={path}, "
            f"完整URL={url}, 超时={timeout}秒, 认证类型={self.auth_type}, "
            f"查询参数={query_preview}, "
            f"时间范围参数: start={params.get('start', 'N/A')}, end={params.get('end', 'N/A')}, step={params.get('step', 'N/A')}"
        )
        
        # 增加超时时间，特别是对于 query_range 请求
        actual_timeout = timeout
        if path == "/api/v1/query_range":
            actual_timeout = max(timeout, 30)  # query_range 至少 30 秒超时
            logger.warning(
                f"[Prometheus请求] query_range 请求，增加超时时间至 {actual_timeout} 秒。"
                f"如果仍然超时，可能需要检查 Prometheus 服务性能或减小查询时间范围"
            )

        # Prometheus 通常在内网环境，禁用代理以避免反向代理问题（与健康检查逻辑一致）
        import os
        from urllib.parse import urlparse
        parsed_url = urlparse(self.base_url)
        target_host = parsed_url.hostname or ""
        
        original_no_proxy = os.environ.get("NO_PROXY", "")
        original_no_proxy_lower = os.environ.get("no_proxy", "")
        original_http_proxy = os.environ.get("HTTP_PROXY")
        original_https_proxy = os.environ.get("HTTPS_PROXY")
        original_http_proxy_lower = os.environ.get("http_proxy")
        original_https_proxy_lower = os.environ.get("https_proxy")
        
        try:
            # 将目标主机添加到 NO_PROXY
            no_proxy_list = []
            if original_no_proxy:
                no_proxy_list.extend(original_no_proxy.split(","))
            if target_host and target_host not in no_proxy_list:
                no_proxy_list.append(target_host)
            if "*" not in no_proxy_list:
                no_proxy_list.append("*")
            
            os.environ["NO_PROXY"] = ",".join(no_proxy_list)
            os.environ["no_proxy"] = ",".join(no_proxy_list)
            
            # 临时清除代理环境变量
            if "HTTP_PROXY" in os.environ:
                del os.environ["HTTP_PROXY"]
            if "HTTPS_PROXY" in os.environ:
                del os.environ["HTTPS_PROXY"]
            if "http_proxy" in os.environ:
                del os.environ["http_proxy"]
            if "https_proxy" in os.environ:
                del os.environ["https_proxy"]

            async with httpx.AsyncClient(timeout=actual_timeout) as client:
                try:
                    response = await client.get(url, params=params, headers=headers)
                    logger.warning(
                        f"[Prometheus响应] 状态码={response.status_code}, "
                        f"URL={url}, 响应大小={len(response.content)} 字节"
                    )
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPStatusError as e:
                    # 特殊处理 502 Bad Gateway 等服务器错误
                    error_detail = ""
                    try:
                        if e.response.content:
                            error_detail = e.response.text[:500]
                    except:
                        pass
                    
                    if e.response.status_code == 502:
                        logger.error(
                            f"[Prometheus请求] 502 Bad Gateway - "
                            f"完整URL={url}, base_url={self.base_url}, "
                            f"查询参数={params}, "
                            f"响应内容={error_detail}, "
                            f"提示: 可能是反向代理配置问题或 Prometheus 服务过载。"
                            f"请检查：1) Prometheus 服务是否正常运行 2) 反向代理配置 3) 查询复杂度是否过高"
                        )
                        raise
                    elif e.response.status_code in (503, 504):
                        logger.error(
                            f"[Prometheus请求] {e.response.status_code} - Prometheus 服务可能暂时不可用或超时。"
                            f" 完整URL={url}, 响应内容={error_detail}"
                        )
                        raise
                    else:
                        logger.error(
                            f"[Prometheus请求失败] HTTP {e.response.status_code}: {error_detail}"
                            f" URL={url}, 参数={params}"
                        )
                        raise
                except httpx.TimeoutException as e:
                    logger.error(
                        f"[Prometheus请求] 请求超时 (超时时间={actual_timeout}秒) - "
                        f"完整URL={url}, 查询参数={params.get('query', 'N/A')[:100]}, "
                        f"提示: 查询可能过于复杂或时间范围太大，尝试减小时间范围或简化查询"
                    )
                    raise
                except httpx.RequestError as e:
                    logger.error(
                        f"[Prometheus请求] 网络错误: {str(e)}. "
                        f"完整URL={url}, base_url={self.base_url}, 参数={params}"
                    )
                    raise
                
                status = data.get("status", "unknown")
                data_obj = data.get("data", {})
                result_list = data_obj.get("result", []) if isinstance(data_obj, dict) else []
                result_count = len(result_list) if isinstance(result_list, list) else 0
                
                if status != "success":
                    logger.error(
                        f"[Prometheus请求失败] URL={url}, status={status}, "
                        f"错误类型={data.get('errorType', 'N/A')}, "
                        f"错误信息={data.get('error', 'N/A')}, "
                        f"查询参数={params}"
                    )
                elif result_count == 0:
                    logger.warning(
                        f"[Prometheus请求结果为空] URL={url}, PromQL={params.get('query', 'N/A')}, "
                        f"时间范围={params.get('start', 'N/A')} ~ {params.get('end', 'N/A')}, "
                        f"步长={params.get('step', 'N/A')}秒"
                    )
                
                ttl = max(1, settings.OBSERVABILITY_METRICS_CACHE_SECONDS)
                if ttl:
                    await cache_manager.set(cache_key, data, ttl)
                return data
        finally:
            # 恢复原始代理环境变量
            if original_no_proxy:
                os.environ["NO_PROXY"] = original_no_proxy
            elif "NO_PROXY" in os.environ:
                del os.environ["NO_PROXY"]
            if original_no_proxy_lower:
                os.environ["no_proxy"] = original_no_proxy_lower
            elif "no_proxy" in os.environ:
                del os.environ["no_proxy"]
            if original_http_proxy is not None:
                os.environ["HTTP_PROXY"] = original_http_proxy
            if original_https_proxy is not None:
                os.environ["HTTPS_PROXY"] = original_https_proxy
            if original_http_proxy_lower is not None:
                os.environ["http_proxy"] = original_http_proxy_lower
            if original_https_proxy_lower is not None:
                os.environ["https_proxy"] = original_https_proxy_lower

    def _build_cache_key(self, path: str, params: Dict[str, Any]) -> str:
        payload = {
            "cluster": self.cluster.id,
            "path": path,
            "params": params,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"obs:metrics:{digest}"
