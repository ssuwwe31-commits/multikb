"""
Kubernetes resource synchronization service.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse

import httpx  # type: ignore
from httpx import Timeout, HTTPStatusError, ConnectError, ConnectTimeout

from app.core.logging import logger
from app.core.cache import cache_manager
from app.models.cluster_config import ClusterConfig
from app.services.cluster_config_service import ResourceSnapshotService
from app.services.resource_event_service import ResourceEventService, ResourceSyncStateService
from app.config.settings import settings

DEFAULT_TIMEOUT = Timeout(15.0, connect=5.0)


def _normalize_verify_ssl(verify_option: Any) -> bool:
    """将 verify_ssl 选项标准化为布尔值"""
    if verify_option is None:
        return False
    if isinstance(verify_option, bool):
        return verify_option
    if isinstance(verify_option, int):
        return bool(verify_option)
    if isinstance(verify_option, str):
        if verify_option.isdigit():
            return bool(int(verify_option))
        return verify_option.lower() in ("true", "1", "yes", "on")
    return bool(verify_option)

RESOURCE_ENDPOINTS = {
    "pods": "/api/v1/namespaces/{namespace}/pods",
    "deployments": "/apis/apps/v1/namespaces/{namespace}/deployments",
    "statefulsets": "/apis/apps/v1/namespaces/{namespace}/statefulsets",
    "daemonsets": "/apis/apps/v1/namespaces/{namespace}/daemonsets",
    "replicasets": "/apis/apps/v1/namespaces/{namespace}/replicasets",
    "jobs": "/apis/batch/v1/namespaces/{namespace}/jobs",
    "cronjobs": "/apis/batch/v1/namespaces/{namespace}/cronjobs",
    "services": "/api/v1/namespaces/{namespace}/services",
    "configmaps": "/api/v1/namespaces/{namespace}/configmaps",
    "secrets": "/api/v1/namespaces/{namespace}/secrets",
    "events": "/api/v1/namespaces/{namespace}/events",
    "nodes": "/api/v1/nodes",
    "resourcequotas": "/api/v1/namespaces/{namespace}/resourcequotas",
    "networkpolicies": "/apis/networking.k8s.io/v1/namespaces/{namespace}/networkpolicies",
    "persistentvolumeclaims": "/api/v1/namespaces/{namespace}/persistentvolumeclaims",
    "namespaces": "/api/v1/namespaces",
}


class KubernetesResourceSyncService:
    """Service responsible for synchronising Kubernetes resources."""

    def __init__(
        self,
        cluster: ClusterConfig,
        snapshot_service: ResourceSnapshotService,
        runtime_config: Optional[Dict[str, Any]] = None,
    ):
        self.cluster = cluster
        self.snapshot_service = snapshot_service
        self.runtime_config = runtime_config or {}
        self.event_service = ResourceEventService(snapshot_service.db)
        self.sync_state_service = ResourceSyncStateService(snapshot_service.db)
        self._namespace_cache: Optional[List[str]] = None

    async def sync_resources(
        self,
        namespace: Optional[str],
        resource_types: List[str],
        limit: Optional[int] = None,
        force_full_sync: bool = False,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        cluster_unreachable = False  # 标记集群是否不可达
        
        for resource_type in resource_types:
            # 如果集群已标记为不可达，跳过所有后续资源类型
            if cluster_unreachable:
                logger.warning(
                    f"跳过资源类型 {resource_type} 的同步: 集群 {self.cluster.name} 不可达"
                )
                results[resource_type] = {
                    "status": "skipped",
                    "count": 0,
                    "resource_version": None,
                    "events": [],
                    "message": f"集群 {self.cluster.name} 不可达，已跳过",
                }
                continue
                
            try:
                target_namespaces = await self._resolve_namespaces(namespace, resource_type)
                aggregated_events: List[Dict[str, Any]] = []
                total_count = 0
                status = "ok"
                last_resource_version: Optional[str] = None

                if not target_namespaces:
                    target_namespaces = [None]

                for ns in target_namespaces:
                    single = await self._sync_resource(resource_type, ns, limit, force_full_sync=force_full_sync)
                    if single.get("status") != "ok":
                        status = single.get("status")
                    total_count += single.get("count", 0)
                    aggregated_events.extend(single.get("events", []))
                    last_resource_version = single.get("resource_version") or last_resource_version

                results[resource_type] = {
                    "status": status,
                    "count": total_count,
                    "resource_version": last_resource_version,
                    "events": aggregated_events,
                    "namespaces": target_namespaces,
                }
            except ConnectionError as conn_exc:
                # 连接错误：集群不可达，标记并跳过后续所有资源类型
                cluster_unreachable = True
                error_msg = str(conn_exc)
                logger.error(
                    f"Resource sync failed (集群不可达): 集群={self.cluster.name}, "
                    f"资源类型={resource_type}, 命名空间={namespace}, 错误信息={error_msg}"
                )
                results[resource_type] = {
                    "status": "error",
                    "count": 0,
                    "resource_version": None,
                    "events": [],
                    "message": error_msg,
                }
                # 跳过后续所有资源类型
                logger.warning(
                    f"集群 {self.cluster.name} 不可达，跳过剩余 {len(resource_types) - resource_types.index(resource_type) - 1} 个资源类型的同步"
                )
            except Exception as exc:  # pylint: disable=broad-except
                # 获取详细的错误信息
                error_type = type(exc).__name__
                # 尝试从异常对象中提取详细信息
                error_msg = ""
                if hasattr(exc, "message") and exc.message:
                    error_msg = str(exc.message)
                elif hasattr(exc, "args") and exc.args:
                    error_msg = str(exc.args[0]) if exc.args[0] else ""
                if not error_msg:
                    error_msg = str(exc) if str(exc) else f"{error_type}异常"
                
                # 对于 httpx.ConnectError，尝试获取更多信息
                if error_type == "ConnectError" and hasattr(exc, "request"):
                    try:
                        request = exc.request
                        error_msg = f"无法连接到 {request.url.host}:{request.url.port or 443} - {error_msg}"
                    except Exception:
                        pass
                
                # 对于 HTTPStatusError，提取状态码和更友好的错误信息
                if error_type == "HTTPStatusError" and hasattr(exc, "response"):
                    try:
                        response = exc.response
                        status_code = response.status_code
                        if status_code == 403:
                            # 尝试从响应中提取更详细的错误信息
                            error_detail = ""
                            try:
                                error_body = response.json()
                                if "message" in error_body:
                                    error_detail = error_body["message"]
                                elif "reason" in error_body:
                                    error_detail = error_body["reason"]
                            except Exception:
                                pass
                            
                            # 构建 RBAC 配置建议
                            rbac_suggestion = ""
                            if resource_type == "secrets":
                                rbac_suggestion = (
                                    "\n解决方案：为 ServiceAccount 授予 secrets 资源的访问权限。"
                                    "\n示例 RBAC 配置请查看日志中的详细说明。"
                                )
                            else:
                                rbac_suggestion = (
                                    f"\n解决方案：为 ServiceAccount 授予 {resource_type} 资源的访问权限（需要 get, list, watch 权限）。"
                                )
                            
                            error_msg = (
                                f"权限不足（403 Forbidden）：当前 Token 没有访问 {resource_type} 资源的权限。"
                                f"{' 错误详情：' + error_detail if error_detail else ''}"
                                f"{rbac_suggestion}"
                            )
                        elif status_code == 404:
                            error_msg = f"资源不存在（404 Not Found）：{resource_type} 资源类型可能不存在或命名空间不存在"
                        elif status_code == 401:
                            error_msg = f"认证失败（401 Unauthorized）：Token 可能已过期或无效"
                        else:
                            error_msg = f"HTTP {status_code} 错误：{error_msg}"
                    except Exception:
                        pass
                
                # 根据错误类型选择日志级别
                # 403 权限错误通常是正常的（secrets 等资源需要特殊权限），使用 INFO
                # PermissionError 也是权限问题，使用 INFO
                # 其他错误使用 ERROR
                if error_type == "PermissionError" or "403" in error_msg or "权限不足" in error_msg:
                    logger.info(
                        "Resource sync skipped (权限限制): 集群=%s, 资源类型=%s, 命名空间=%s, 错误信息=%s",
                        self.cluster.name,
                        resource_type,
                        namespace,
                        error_msg
                    )
                    results[resource_type] = {"status": "skipped", "message": error_msg}
                else:
                    logger.error(
                        "Resource sync failed: 集群=%s, 资源类型=%s, 命名空间=%s, 错误类型=%s, 错误信息=%s",
                        self.cluster.name,
                        resource_type,
                        namespace,
                        error_type,
                        error_msg,
                        exc_info=True
                    )
                    results[resource_type] = {"status": "error", "message": error_msg}
        return results

    async def _resolve_namespaces(self, namespace: Optional[str], resource_type: str) -> List[Optional[str]]:
        endpoint = RESOURCE_ENDPOINTS.get(resource_type)
        if not endpoint:
            return [namespace]
        requires_namespace = "{namespace}" in endpoint
        if not requires_namespace:
            return [namespace]

        if namespace:
            return [namespace]

        if settings.OBSERVABILITY_DEFAULT_NAMESPACE:
            return [settings.OBSERVABILITY_DEFAULT_NAMESPACE]

        tracked = getattr(settings, "OBSERVABILITY_TRACKED_NAMESPACES", None)
        if tracked:
            return tracked

        return await self._get_all_namespaces()

    async def _get_all_namespaces(self) -> List[str]:
        if self._namespace_cache is not None:
            return self._namespace_cache
        try:
            payload = await self._fetch_resource("namespaces", None, None, None)
            items = payload.get("items", [])
            namespaces = [
                item.get("metadata", {}).get("name")
                for item in items
                if item.get("metadata", {}).get("name")
            ]
            if not namespaces:
                namespaces = ["default"]
            self._namespace_cache = namespaces
            logger.info("同步任务：自动发现命名空间 %s", ",".join(namespaces))
            return namespaces
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("获取命名空间列表失败，回退到 ['default']: %s", exc)
            self._namespace_cache = ["default"]
            return self._namespace_cache

    async def _sync_resource(
        self, 
        resource_type: str, 
        namespace: Optional[str], 
        limit: Optional[int],
        force_full_sync: bool = False,
    ) -> Dict[str, Any]:
        from datetime import datetime, timedelta
        import uuid
        
        # 生成锁的 key 和 value
        lock_key = f"sync_lock:{self.cluster.id}:{resource_type}:{namespace or '*'}"
        lock_value = str(uuid.uuid4())
        lock_timeout = 600  # 锁的超时时间：10分钟（足够长的同步时间）
        
        # 尝试获取分布式锁，防止并发同步
        lock_acquired = await cache_manager.acquire_lock(lock_key, timeout=lock_timeout, value=lock_value)
        if not lock_acquired:
            logger.warning(
                f"同步任务已在进行中，跳过本次同步: 集群={self.cluster.name}, "
                f"资源类型={resource_type}, 命名空间={namespace}"
            )
            return {
                "status": "skipped",
                "count": 0,
                "resource_version": None,
                "events": [],
                "message": "同步任务已在进行中，跳过本次同步",
            }
        
        # 使用 try-finally 确保锁被释放
        try:
            state = await self.sync_state_service.get_state(self.cluster.id, resource_type, namespace)
            last_resource_version = state.resource_version if state else None

            events: List[Dict[str, Any]] = []
            seen_uids: Set[str] = set()

            # 决定是否使用增量同步
            # 策略：如果强制全量同步，跳过增量同步
            # 否则：如果有 resource_version 且距离上次同步时间不太久，使用增量同步
            # 否则使用全量同步以确保一致性
            use_incremental = False
            incremental_success = False
            
            if force_full_sync:
                # 强制全量同步，跳过增量同步判断
                logger.info(
                    f"强制全量同步: 集群={self.cluster.name}, 资源类型={resource_type}, 命名空间={namespace}"
                )
            elif last_resource_version and state and state.updated_at:
                time_since_last_sync = datetime.utcnow() - state.updated_at.replace(tzinfo=None) if state.updated_at else timedelta(days=1)
                # 获取配置的同步间隔
                sync_interval = timedelta(seconds=settings.OBSERVABILITY_SYNC_INTERVAL_SECONDS)
                # 如果距离上次同步超过同步间隔的 1/3，禁用增量同步（避免频繁 Watch 失败）
                # 同时考虑 K8s 默认只保留 5 分钟的 watch 事件，取两者较小值
                max_incremental_window = min(timedelta(minutes=5), sync_interval / 3)
                use_incremental = time_since_last_sync < max_incremental_window
                
                if not use_incremental:
                    logger.debug(
                        f"距离上次同步超过增量同步窗口（{max_incremental_window}），跳过增量同步: 集群={self.cluster.name}, "
                        f"资源类型={resource_type}, 命名空间={namespace}, 距离上次同步={time_since_last_sync}"
                    )

            if use_incremental and last_resource_version:
                logger.debug(
                    f"开始增量同步: 集群={self.cluster.name}, 资源类型={resource_type}, "
                    f"命名空间={namespace}, 上次版本={last_resource_version}, "
                    f"距离上次同步={time_since_last_sync}"
                )
                attempts = max(1, settings.OBSERVABILITY_WATCH_MAX_ATTEMPTS)
                rv_candidate = last_resource_version
                watch_success = False
                for attempt in range(attempts):
                    try:
                        watch_events, latest_rv = await self._watch_resource(resource_type, namespace, rv_candidate)
                        if latest_rv:
                            rv_candidate = latest_rv
                            watch_success = True
                        processed = 0
                        for event in watch_events:
                            summary = await self._process_watch_event(resource_type, namespace, event)
                            if summary:
                                events.append(summary)
                                processed += 1
                                if summary["type"] != "deleted":
                                    seen_uids.add(summary["uid"])
                        if processed or latest_rv:
                            watch_success = True
                            break
                    except Exception as exc:
                        # 只在最后一次尝试失败时记录警告，中间尝试只记录 debug
                        if attempt == attempts - 1:
                            logger.warning(
                                f"增量同步 watch 失败（已重试 {attempts} 次）: 集群={self.cluster.name}, "
                                f"资源类型={resource_type}, 命名空间={namespace}, 错误={exc}"
                            )
                            watch_success = False
                        else:
                            logger.debug(
                                f"增量同步 watch 失败 (尝试 {attempt + 1}/{attempts}): 集群={self.cluster.name}, "
                                f"资源类型={resource_type}, 命名空间={namespace}, 错误={exc}"
                            )
                
                if watch_success:
                    incremental_success = True
                    last_resource_version = rv_candidate
                    if events:
                        logger.debug(
                            f"增量同步完成: 集群={self.cluster.name}, 资源类型={resource_type}, "
                            f"命名空间={namespace}, 变更事件数={len(events)}, 新版本={rv_candidate}"
                        )
                    else:
                        logger.debug(
                            f"增量同步完成（无变更）: 集群={self.cluster.name}, 资源类型={resource_type}, "
                            f"命名空间={namespace}, 新版本={rv_candidate}"
                        )
                else:
                    logger.info(
                        f"增量同步失败，回退到全量同步: 集群={self.cluster.name}, 资源类型={resource_type}, "
                        f"命名空间={namespace}"
                    )
            else:
                if last_resource_version:
                    time_since_last_sync = (
                        datetime.utcnow() - state.updated_at.replace(tzinfo=None) 
                        if state and state.updated_at else timedelta(days=1)
                    )
                    logger.info(
                        f"强制全量同步（确保一致性）: 集群={self.cluster.name}, 资源类型={resource_type}, "
                        f"命名空间={namespace}, 上次版本={last_resource_version}, "
                        f"距离上次同步={time_since_last_sync}"
                    )
                else:
                    logger.debug(
                        f"首次全量同步: 集群={self.cluster.name}, 资源类型={resource_type}, 命名空间={namespace}"
                    )

            # 无论增量同步是否成功，都执行全量同步以确保数据完整性
            # 增量同步可能漏掉一些变更（例如 watch 开始之前的变更、watch 超时期间的变更等）
            # 全量同步可以检测到所有资源的实际变更状态
            # 如果增量同步成功，使用最新的 resource_version 进行全量同步以提高效率
            # 执行全量同步（首次同步、增量同步失败、或增量同步无变更时）
            # 即使增量同步成功且捕获到变更，仍然需要全量同步以确保数据完整性（避免漏掉其他资源的变更）
            # 使用当前的 resource_version 进行全量同步，确保获取到最新的完整列表
            # 如果增量同步成功，last_resource_version 已经是新的版本，全量同步时使用它
            # 注意：如果距离上次同步超过 5 分钟，resourceVersion 可能已过期，直接使用 None 进行全量同步
            fetch_resource_version = None  # 默认不使用 resourceVersion（避免 410 错误）
            if last_resource_version and state and state.updated_at:
                time_since_last_sync = datetime.utcnow() - state.updated_at.replace(tzinfo=None) if state.updated_at else timedelta(days=1)
                # 如果距离上次同步不超过 5 分钟，可以使用 resourceVersion 进行全量同步
                if time_since_last_sync < timedelta(minutes=5):
                    fetch_resource_version = last_resource_version
            
            try:
                payload = await self._fetch_resource(resource_type, namespace, limit, fetch_resource_version)
            except HTTPStatusError as exc:
                # 处理 410 Gone 错误：resourceVersion 已过期，需要清除并重新全量同步
                if exc.response.status_code == 410:
                    logger.warning(
                        f"ResourceVersion 已过期（410 Gone），清除并重新全量同步: 集群={self.cluster.name}, "
                        f"资源类型={resource_type}, 命名空间={namespace}, 过期版本={last_resource_version}"
                    )
                    # 清除同步状态中存储的过期 resource_version
                    await self.sync_state_service.set_state(self.cluster.id, resource_type, namespace, None)
                    # 清除 last_resource_version，重新进行全量同步（不带 resourceVersion 参数）
                    last_resource_version = None
                    payload = await self._fetch_resource(resource_type, namespace, limit, None)
                else:
                    # 其他 HTTP 错误直接抛出
                    raise
            
            items = payload.get("items", [])

            for item in items:
                meta = item.get("metadata") or {}
                uid = meta.get("uid") or f"{namespace or ''}/{meta.get('name')}"
                name = meta.get("name") or uid
                resource_version = meta.get("resourceVersion")
                labels = meta.get("labels")
                annotations = meta.get("annotations")
                spec = item.get("spec")
                status = item.get("status")
                seen_uids.add(uid)

                change_type, diff = await self.snapshot_service.upsert_snapshot(
                    {
                        "cluster_id": self.cluster.id,
                        "resource_uid": uid,
                        "resource_type": resource_type,
                        "namespace": namespace,
                        "resource_name": name,
                        "labels": labels,
                        "annotations": annotations,
                        "spec": spec,
                        "status": status,
                        "resource_version": resource_version,
                        "snapshot": item,
                    }
                )
                if change_type != "none":
                    await self.event_service.create_event(
                        {
                            "cluster_id": self.cluster.id,
                            "resource_type": resource_type,
                            "namespace": namespace,
                            "resource_uid": uid,
                            "event_type": change_type,
                            "diff": diff,
                        }
                    )
                    events.append({"uid": uid, "type": change_type, "diff": diff})

            deleted_records = await self.snapshot_service.mark_absent(
                cluster_id=self.cluster.id,
                resource_type=resource_type,
                namespace=namespace,
                existing_uids=seen_uids,
            )
            for record in deleted_records:
                await self.event_service.create_event(
                    {
                        "cluster_id": self.cluster.id,
                        "resource_type": resource_type,
                        "namespace": namespace,
                        "resource_uid": record["resource_uid"],
                        "event_type": "deleted",
                        "diff": record.get("diff"),
                    }
                )
                events.append({"uid": record["resource_uid"], "type": "deleted", "diff": record.get("diff")})

            new_resource_version = payload.get("metadata", {}).get("resourceVersion") or last_resource_version
            if new_resource_version:
                await self.sync_state_service.set_state(self.cluster.id, resource_type, namespace, new_resource_version)
                logger.debug(
                    f"更新同步状态: 集群={self.cluster.name}, 资源类型={resource_type}, "
                    f"命名空间={namespace}, 新版本={new_resource_version}"
                )

            return {
                "status": "ok",
                "count": len(items),
                "resource_version": new_resource_version,
                "events": events,
            }
        finally:
            # 确保释放分布式锁
            await cache_manager.release_lock(lock_key, lock_value)

    async def _fetch_resource(
        self,
        resource_type: str,
        namespace: Optional[str],
        limit: Optional[int] = None,
        resource_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        if resource_type not in RESOURCE_ENDPOINTS:
            raise ValueError(f"Unsupported resource type: {resource_type}")

        base_url = self.cluster.api_server.rstrip("/")
        if "{namespace}" in RESOURCE_ENDPOINTS[resource_type]:
            ns = namespace or settings.OBSERVABILITY_DEFAULT_NAMESPACE
            if not ns:
                raise ValueError(f"Namespace is required for resource type {resource_type}")
            path = RESOURCE_ENDPOINTS[resource_type].format(namespace=ns)
        else:
            ns = namespace or settings.OBSERVABILITY_DEFAULT_NAMESPACE
            path = RESOURCE_ENDPOINTS[resource_type]

        params = {}
        if limit:
            params["limit"] = limit
        if resource_version:
            params["resourceVersion"] = resource_version

        headers: Dict[str, str] = {}
        auth_type = self.runtime_config.get("auth_type") or self.cluster.auth_type or "token"
        auth_token = self.runtime_config.get("auth_token") or self.cluster.auth_token
        if auth_type == "token" and auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        elif auth_type == "basic" and auth_token:
            headers["Authorization"] = auth_token

        url = urljoin(base_url + "/", path.lstrip("/"))
        verify_option: Any = self.runtime_config.get("verify_ssl", self.cluster.verify_ssl)
        verify_ssl = _normalize_verify_ssl(verify_option)
        
        # 对于 K8s API Server，通常在内网环境，不应该使用代理
        # 禁用代理以避免连接问题
        parsed_url = urlparse(url)
        target_host = parsed_url.hostname or ""
        
        # 保存原始代理环境变量
        original_no_proxy = os.environ.get("NO_PROXY", "")
        original_no_proxy_lower = os.environ.get("no_proxy", "")
        original_proxy = os.environ.pop("HTTP_PROXY", None)
        original_https_proxy = os.environ.pop("HTTPS_PROXY", None)
        original_http_proxy = os.environ.pop("http_proxy", None)
        original_https_proxy_lower = os.environ.pop("https_proxy", None)
        
        try:
            # 将目标主机添加到 NO_PROXY，并禁用所有代理
            no_proxy_list = []
            if original_no_proxy:
                no_proxy_list.extend(original_no_proxy.split(","))
            if target_host and target_host not in no_proxy_list:
                no_proxy_list.append(target_host)
            # 添加通配符来禁用所有代理
            if "*" not in no_proxy_list:
                no_proxy_list.append("*")
            
            os.environ["NO_PROXY"] = ",".join(no_proxy_list)
            os.environ["no_proxy"] = ",".join(no_proxy_list)
            
            logger.debug(
                f"准备连接: 集群={self.cluster.name}, URL={url}, verify_ssl={verify_ssl}, "
                f"auth_type={auth_type}, timeout={DEFAULT_TIMEOUT}, NO_PROXY={os.environ.get('NO_PROXY')}"
            )

            # 显式禁用代理（通过环境变量 NO_PROXY 和清除代理环境变量）
            async with httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                verify=verify_ssl
            ) as client:
                try:
                    response = await client.get(url, headers=headers, params=params)
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException) as conn_err:
                    # 连接错误：集群不可达或网络问题
                    # 注意：httpx 可能抛出 httpcore.ConnectError，但会被 httpx.ConnectError 捕获
                    error_msg = f"无法连接到 {self.cluster.name} 集群 ({self.cluster.api_server}) - {str(conn_err)}"
                    logger.error(
                        f"Resource sync connection failed: 集群={self.cluster.name}, "
                        f"资源类型={resource_type}, 命名空间={namespace}, "
                        f"错误类型={type(conn_err).__name__}, 错误信息={error_msg}"
                    )
                    # 转换为 ConnectionError，让上层调用者可以统一处理
                    raise ConnectionError(error_msg) from conn_err
                except httpx.HTTPStatusError as http_err:
                    # HTTP 状态错误（如 404, 500 等）
                    if http_err.response.status_code == 403:
                        # 403 错误会在下面单独处理
                        raise
                    error_msg = f"HTTP 错误 {http_err.response.status_code}: {str(http_err)}"
                    logger.error(
                        f"Resource sync HTTP error: 集群={self.cluster.name}, "
                        f"资源类型={resource_type}, 命名空间={namespace}, "
                        f"状态码={http_err.response.status_code}, 错误信息={error_msg}"
                    )
                    raise
                
                # 对于 403 权限错误，提供详细的错误信息和解决建议
                if response.status_code == 403:
                    # 尝试从响应中提取更详细的错误信息
                    error_detail = ""
                    try:
                        error_body = response.json()
                        if "message" in error_body:
                            error_detail = error_body["message"]
                        elif "reason" in error_body:
                            error_detail = error_body["reason"]
                    except Exception:
                        pass
                    
                    # 构建友好的错误信息和 RBAC 配置建议
                    rbac_suggestion = ""
                    if resource_type == "secrets":
                        rbac_suggestion = (
                            "\n解决方案：为 ServiceAccount 授予 secrets 资源的访问权限。"
                            "\n示例 RBAC 配置："
                            "\n---"
                            "\napiVersion: rbac.authorization.k8s.io/v1"
                            "\nkind: ClusterRole"
                            "\nmetadata:"
                            "\n  name: secrets-reader"
                            "\nrules:"
                            "\n- apiGroups: [\"\"]"
                            "\n  resources: [\"secrets\"]"
                            "\n  verbs: [\"get\", \"list\", \"watch\"]"
                            "\n---"
                            "\napiVersion: rbac.authorization.k8s.io/v1"
                            "\nkind: ClusterRoleBinding"
                            "\nmetadata:"
                            "\n  name: secrets-reader-binding"
                            "\nroleRef:"
                            "\n  apiGroup: rbac.authorization.k8s.io"
                            "\n  kind: ClusterRole"
                            "\n  name: secrets-reader"
                            "\nsubjects:"
                            "\n- kind: ServiceAccount"
                            "\n  name: <your-service-account>"
                            "\n  namespace: <namespace>"
                        )
                    else:
                        rbac_suggestion = (
                            f"\n解决方案：为 ServiceAccount 授予 {resource_type} 资源的访问权限。"
                            f"\n需要以下权限：get, list, watch"
                        )
                    
                    error_msg = (
                        f"权限不足（403 Forbidden）：当前 Token 没有访问 {resource_type} 资源的权限。"
                        f"{' 错误详情：' + error_detail if error_detail else ''}"
                        f"{rbac_suggestion}"
                    )
                    logger.warning(
                        f"资源同步跳过（权限限制）: 集群={self.cluster.name}, 资源类型={resource_type}, "
                        f"命名空间={ns}, URL={url}"
                        f"{' 错误详情：' + error_detail if error_detail else ''}"
                    )
                    raise PermissionError(error_msg)
                
                response.raise_for_status()
                data = response.json()
                return data
        finally:
            # 恢复原始环境变量
            if original_proxy is not None:
                os.environ["HTTP_PROXY"] = original_proxy
            if original_https_proxy is not None:
                os.environ["HTTPS_PROXY"] = original_https_proxy
            if original_http_proxy is not None:
                os.environ["http_proxy"] = original_http_proxy
            if original_https_proxy_lower is not None:
                os.environ["https_proxy"] = original_https_proxy_lower
            if original_no_proxy:
                os.environ["NO_PROXY"] = original_no_proxy
            elif "NO_PROXY" in os.environ:
                del os.environ["NO_PROXY"]
            if original_no_proxy_lower:
                os.environ["no_proxy"] = original_no_proxy_lower
            elif "no_proxy" in os.environ:
                del os.environ["no_proxy"]

    async def _watch_resource(
        self,
        resource_type: str,
        namespace: Optional[str],
        resource_version: str,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        events: List[Dict[str, Any]] = []
        latest_rv: Optional[str] = resource_version
        try:
            base_url = self.cluster.api_server.rstrip("/")
            if "{namespace}" in RESOURCE_ENDPOINTS[resource_type]:
                ns = namespace or settings.OBSERVABILITY_DEFAULT_NAMESPACE
                if not ns:
                    raise ValueError(f"Namespace is required for resource type {resource_type}")
                path = RESOURCE_ENDPOINTS[resource_type].format(namespace=ns)
            else:
                path = RESOURCE_ENDPOINTS[resource_type]
            url = urljoin(base_url + "/", path.lstrip("/"))

            params = {
                "watch": "true",
                "resourceVersion": resource_version,
                "timeoutSeconds": settings.OBSERVABILITY_WATCH_TIMEOUT_SECONDS,
            }
            headers: Dict[str, str] = {}
            auth_type = self.runtime_config.get("auth_type") or self.cluster.auth_type or "token"
            auth_token = self.runtime_config.get("auth_token") or self.cluster.auth_token
            if auth_type == "token" and auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            elif auth_type == "basic" and auth_token:
                headers["Authorization"] = auth_token

            verify_option: Any = self.runtime_config.get("verify_ssl", self.cluster.verify_ssl)
            verify_ssl = _normalize_verify_ssl(verify_option)
            
            # 禁用代理（与 _fetch_resource 相同的逻辑）
            parsed_url = urlparse(url)
            target_host = parsed_url.hostname or ""
            original_no_proxy = os.environ.get("NO_PROXY", "")
            original_no_proxy_lower = os.environ.get("no_proxy", "")
            original_proxy = os.environ.pop("HTTP_PROXY", None)
            original_https_proxy = os.environ.pop("HTTPS_PROXY", None)
            original_http_proxy = os.environ.pop("http_proxy", None)
            original_https_proxy_lower = os.environ.pop("https_proxy", None)
            
            try:
                no_proxy_list = []
                if original_no_proxy:
                    no_proxy_list.extend(original_no_proxy.split(","))
                if target_host and target_host not in no_proxy_list:
                    no_proxy_list.append(target_host)
                if "*" not in no_proxy_list:
                    no_proxy_list.append("*")
                os.environ["NO_PROXY"] = ",".join(no_proxy_list)
                os.environ["no_proxy"] = ",".join(no_proxy_list)
                
                # 显式禁用代理（通过环境变量 NO_PROXY 和清除代理环境变量）
                async with httpx.AsyncClient(
                    timeout=None,
                    verify=verify_ssl
                ) as client:
                    async with client.stream("GET", url, headers=headers, params=params) as response:
                        if response.status_code == 410:
                            logger.info("Watch for %s returned resourceVersion too old, fallback to list", resource_type)
                            return [], None
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            events.append(data)
                            rv = ((data.get("object") or {}).get("metadata") or {}).get("resourceVersion")
                            if rv:
                                latest_rv = rv
            finally:
                # 恢复原始环境变量
                if original_proxy is not None:
                    os.environ["HTTP_PROXY"] = original_proxy
                if original_https_proxy is not None:
                    os.environ["HTTPS_PROXY"] = original_https_proxy
                if original_http_proxy is not None:
                    os.environ["http_proxy"] = original_http_proxy
                if original_https_proxy_lower is not None:
                    os.environ["https_proxy"] = original_https_proxy_lower
                if original_no_proxy:
                    os.environ["NO_PROXY"] = original_no_proxy
                elif "NO_PROXY" in os.environ:
                    del os.environ["NO_PROXY"]
                if original_no_proxy_lower:
                    os.environ["no_proxy"] = original_no_proxy_lower
                elif "no_proxy" in os.environ:
                    del os.environ["no_proxy"]
        except Exception as exc:  # pylint: disable=broad-except
            # Watch 失败是常见情况（网络问题、K8s API 限制等），使用 debug 级别减少日志噪音
            logger.debug("Watch failed for %s: %s", resource_type, exc)
            return [], None
        return events, latest_rv

    async def _process_watch_event(
        self,
        resource_type: str,
        namespace: Optional[str],
        event: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        event_type = (event.get("type") or "").lower()
        obj = event.get("object") or {}
        meta = obj.get("metadata") or {}
        uid = meta.get("uid")
        if not uid:
            return None

        if event_type in ("added", "modified"):
            name = meta.get("name") or uid
            resource_version = meta.get("resourceVersion")
            labels = meta.get("labels")
            annotations = meta.get("annotations")
            spec = obj.get("spec")
            status = obj.get("status")
            change_type, diff = await self.snapshot_service.upsert_snapshot(
                {
                    "cluster_id": self.cluster.id,
                    "resource_uid": uid,
                    "resource_type": resource_type,
                    "namespace": namespace,
                    "resource_name": name,
                    "labels": labels,
                    "annotations": annotations,
                    "spec": spec,
                    "status": status,
                    "resource_version": resource_version,
                    "snapshot": obj,
                }
            )
            if change_type == "none":
                return None
            await self.event_service.create_event(
                {
                    "cluster_id": self.cluster.id,
                    "resource_type": resource_type,
                    "namespace": namespace,
                    "resource_uid": uid,
                    "event_type": change_type,
                    "diff": diff,
                }
            )
            return {"uid": uid, "type": change_type, "diff": diff}

        if event_type == "deleted":
            deleted = await self.snapshot_service.delete_snapshot(self.cluster.id, uid)
            if not deleted:
                return None
            await self.event_service.create_event(
                {
                    "cluster_id": self.cluster.id,
                    "resource_type": resource_type,
                    "namespace": namespace,
                    "resource_uid": uid,
                    "event_type": "deleted",
                    "diff": deleted.get("diff"),
                }
            )
            return {"uid": uid, "type": "deleted", "diff": deleted.get("diff")}

        return None

    async def fetch_resource_detail(
        self,
        resource_type: str,
        namespace: Optional[str],
        name: str,
    ) -> Dict[str, Any]:
        payload = await self._fetch_resource(resource_type, namespace, None, None)
        for item in payload.get("items", []):
            if item.get("metadata", {}).get("name") == name:
                return item
        raise ValueError(f"Resource {name} not found in {resource_type}")

    async def fetch_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = 100,
        since_seconds: Optional[int] = None,
    ) -> str:
        """
        从 Kubernetes API Server 直接获取 Pod 日志（实时日志）
        
        Args:
            namespace: Pod 所在的命名空间
            pod_name: Pod 名称
            container: 容器名称（可选，多容器 Pod 需要指定）
            tail_lines: 获取最后 N 行日志（默认 100）
            since_seconds: 获取最近 N 秒的日志（可选）
        
        Returns:
            日志内容（字符串）
        
        Raises:
            httpx.HTTPStatusError: 如果 Pod 不存在或无法获取日志
        """
        base_url = self.cluster.api_server.rstrip("/")
        path = f"/api/v1/namespaces/{namespace}/pods/{pod_name}/log"
        
        params: Dict[str, Any] = {}
        if container:
            params["container"] = container
        if tail_lines:
            params["tailLines"] = tail_lines
        if since_seconds:
            params["sinceSeconds"] = since_seconds
        
        headers: Dict[str, str] = {}
        auth_type = self.runtime_config.get("auth_type") or self.cluster.auth_type or "token"
        auth_token = self.runtime_config.get("auth_token") or self.cluster.auth_token
        if auth_type == "token" and auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        elif auth_type == "basic" and auth_token:
            headers["Authorization"] = auth_token
        
        url = urljoin(base_url + "/", path.lstrip("/"))
        verify_option: Any = self.runtime_config.get("verify_ssl", self.cluster.verify_ssl)
        verify_ssl = _normalize_verify_ssl(verify_option)
        
        # 禁用代理（与 _fetch_resource 相同的逻辑）
        parsed_url = urlparse(url)
        target_host = parsed_url.hostname or ""
        original_no_proxy = os.environ.get("NO_PROXY", "")
        original_no_proxy_lower = os.environ.get("no_proxy", "")
        original_proxy = os.environ.pop("HTTP_PROXY", None)
        original_https_proxy = os.environ.pop("HTTPS_PROXY", None)
        original_http_proxy = os.environ.pop("http_proxy", None)
        original_https_proxy_lower = os.environ.pop("https_proxy", None)
        
        try:
            no_proxy_list = []
            if original_no_proxy:
                no_proxy_list.extend(original_no_proxy.split(","))
            if target_host and target_host not in no_proxy_list:
                no_proxy_list.append(target_host)
            if "*" not in no_proxy_list:
                no_proxy_list.append("*")
            os.environ["NO_PROXY"] = ",".join(no_proxy_list)
            os.environ["no_proxy"] = ",".join(no_proxy_list)
            
            # 显式禁用代理（通过环境变量 NO_PROXY 和清除代理环境变量）
            async with httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                verify=verify_ssl
            ) as client:
                logger.warning(
                    f"[K8s API 日志请求] URL={url}, "
                    f"参数={params}, "
                    f"命名空间={namespace}, Pod={pod_name}, 容器={container or '默认'}"
                )
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                log_text = response.text
                log_length = len(log_text) if log_text else 0
                log_lines_count = len(log_text.strip().split("\n")) if log_text else 0
                logger.warning(
                    f"[K8s API 日志响应] 状态码={response.status_code}, "
                    f"响应长度={log_length} 字符, "
                    f"日志行数={log_lines_count}, "
                    f"前100字符={log_text[:100] if log_text else '(空)'}"
                )
                return log_text
        finally:
            # 恢复原始环境变量
            if original_proxy is not None:
                os.environ["HTTP_PROXY"] = original_proxy
            if original_https_proxy is not None:
                os.environ["HTTPS_PROXY"] = original_https_proxy
            if original_http_proxy is not None:
                os.environ["http_proxy"] = original_http_proxy
            if original_https_proxy_lower is not None:
                os.environ["https_proxy"] = original_https_proxy_lower
            if original_no_proxy:
                os.environ["NO_PROXY"] = original_no_proxy
            elif "NO_PROXY" in os.environ:
                del os.environ["NO_PROXY"]
            if original_no_proxy_lower:
                os.environ["no_proxy"] = original_no_proxy_lower
            elif "no_proxy" in os.environ:
                del os.environ["no_proxy"]


async def list_snapshots(
    snapshot_service: ResourceSnapshotService,
    cluster_id: int,
    resource_type: Optional[str],
    namespace: Optional[str],
    resource_name: Optional[str],
    skip: int,
    limit: int,
) -> Tuple[List[Dict[str, Any]], int]:
    query = snapshot_service.db.query(snapshot_service.model).filter(
        snapshot_service.model.cluster_id == cluster_id,
        snapshot_service.model.is_deleted == False,  # noqa: E712
    )
    if resource_type:
        query = query.filter(snapshot_service.model.resource_type == resource_type)
    if namespace:
        query = query.filter(snapshot_service.model.namespace == namespace)
    if resource_name:
        query = query.filter(snapshot_service.model.resource_name == resource_name)

    total = query.count()
    rows = (
        query.order_by(snapshot_service.model.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    data = []
    for row in rows:
        data.append(
            {
                "id": row.id,
                "cluster_id": row.cluster_id,
                "resource_type": row.resource_type,
                "namespace": row.namespace,
                "resource_uid": row.resource_uid,
                "resource_name": row.resource_name,
                "labels": row.labels,
                "annotations": row.annotations,
                "spec": row.spec,
                "status": row.status,
                "resource_version": row.resource_version,
                "snapshot": row.snapshot,
                "collected_at": row.collected_at,
                "updated_at": row.updated_at,
            }
        )
    return data, total
