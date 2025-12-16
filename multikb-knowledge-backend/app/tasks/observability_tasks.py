"""
Celery tasks for observability workflows.
"""

from __future__ import annotations

import asyncio
from typing import List

from app.config.database import SessionLocal
from app.config.settings import settings
from app.core.logging import logger
from app.models.cluster_config import ClusterConfig
from app.tasks.celery_app import celery_app
from app.services.cluster_config_service import (
    ClusterConfigService,
    ResourceSnapshotService,
)
from app.services.diagnosis_service import DiagnosisService
from app.services.resource_sync_service import KubernetesResourceSyncService

# 确保模型在 Celery 进程中注册
import app.models  # noqa: F401


def _get_active_clusters(service: ClusterConfigService) -> List[ClusterConfig]:
    return service.get_active_configs()


async def _sync_clusters_async(cluster_service: ClusterConfigService, snapshot_service: ResourceSnapshotService) -> None:
    clusters = _get_active_clusters(cluster_service)
    if not clusters:
        logger.info("定时同步任务：没有活跃的集群，跳过同步")
        return
    
    logger.info(f"定时同步任务开始：发现 {len(clusters)} 个活跃集群")
    tasks = []
    task_info = []  # 记录任务信息，用于日志输出
    
    for cluster in clusters:
        runtime = cluster_service.build_runtime_payload(cluster)
        sync_service = KubernetesResourceSyncService(cluster, snapshot_service, runtime)
        
        namespaces = getattr(settings, "OBSERVABILITY_TRACKED_NAMESPACES", None)
        if namespaces:
            target_namespaces = namespaces
        else:
            # None 表示同步所有命名空间
            target_namespaces = [None]

        for namespace in target_namespaces:
            task_info.append(
                {
                    "cluster_id": cluster.id,
                    "cluster_name": cluster.name,
                    "namespace": namespace or "*",
                }
            )
            tasks.append(
                sync_service.sync_resources(
                    namespace=namespace,
                    resource_types=settings.OBSERVABILITY_RESOURCE_TYPES,
                    limit=None,
                )
            )
    
    # 执行所有同步任务并记录结果
    total_synced = 0
    total_errors = 0
    for idx, coro in enumerate(tasks):
        info = task_info[idx]
        try:
            result = await coro
            # 统计同步结果
            synced_count = 0
            error_count = 0
            for resource_type, resource_result in result.items():
                status = resource_result.get("status")
                if status == "ok":
                    count = resource_result.get("count", 0)
                    synced_count += count
                    events = resource_result.get("events", [])
                    logger.info(
                        f"集群同步成功: 集群={info['cluster_name']}(ID:{info['cluster_id']}), "
                        f"命名空间={info['namespace']}, 资源类型={resource_type}, "
                        f"同步数量={count}, 变更事件={len(events)}"
                    )
                elif status == "skipped":
                    # 跳过（通常是权限问题，如 secrets），不算错误
                    error_msg = resource_result.get("message", "已跳过")
                    logger.info(
                        f"集群同步跳过: 集群={info['cluster_name']}(ID:{info['cluster_id']}), "
                        f"命名空间={info['namespace']}, 资源类型={resource_type}, "
                        f"原因={error_msg}"
                    )
                else:
                    error_count += 1
                    error_msg = resource_result.get("message", "未知错误")
                    logger.warning(
                        f"集群同步失败: 集群={info['cluster_name']}(ID:{info['cluster_id']}), "
                        f"命名空间={info['namespace']}, 资源类型={resource_type}, "
                        f"错误={error_msg}"
                    )
            total_synced += synced_count
            total_errors += error_count
        except Exception as exc:  # pylint: disable=broad-except
            total_errors += 1
            logger.error(
                f"集群同步异常: 集群={info['cluster_name']}(ID:{info['cluster_id']}), "
                f"命名空间={info['namespace']}, 错误={exc}",
                exc_info=True
            )
    
    logger.info(
        f"定时同步任务完成: 总集群数={len(clusters)}, "
        f"总同步资源数={total_synced}, 总错误数={total_errors}"
    )


async def _health_check_async(cluster_service: ClusterConfigService) -> None:
    clusters = _get_active_clusters(cluster_service)
    if not clusters:
        logger.info("定时健康检查任务：没有活跃的集群，跳过检查")
        return
    
    logger.info(f"定时健康检查任务开始：发现 {len(clusters)} 个活跃集群")
    success_count = 0
    error_count = 0
    
    for cluster in clusters:
        try:
            result = await cluster_service.run_health_check(cluster)
            success_count += 1
            api_status = result.api_server.status
            logger.info(
                f"集群健康检查成功: 集群={cluster.name}(ID:{cluster.id}), "
                f"API状态={api_status}, "
                f"Prometheus={'已配置' if cluster.prometheus_url else '未配置'}, "
                f"日志系统={'已配置' if cluster.log_endpoint else '未配置'}"
            )
        except Exception as exc:  # pylint: disable=broad-except
            error_count += 1
            logger.error(
                f"集群健康检查失败: 集群={cluster.name}(ID:{cluster.id}), 错误={exc}",
                exc_info=True
            )
    
    logger.info(
        f"定时健康检查任务完成: 总集群数={len(clusters)}, "
        f"成功={success_count}, 失败={error_count}"
    )


@celery_app.task(
    name="app.tasks.observability_tasks.sync_active_clusters",
    priority=settings.CELERY_TASK_PRIORITY_OBSERVABILITY,
    ignore_result=True,  # 忽略结果，避免存储任务结果
)
def sync_active_clusters() -> None:
    """定时同步所有活跃集群关键资源。"""
    if not settings.OBSERVABILITY_ENABLE_SCHEDULE:
        return
    
    # 使用分布式锁防止任务重复执行
    from app.core.cache import cache_manager
    import asyncio
    import uuid
    
    lock_key = "sync_active_clusters_lock"
    lock_timeout = 1800  # 30分钟，与同步间隔相同
    lock_value = str(uuid.uuid4())  # 生成唯一的锁值
    
    # 尝试获取锁
    lock_acquired = asyncio.run(cache_manager.acquire_lock(lock_key, timeout=lock_timeout, value=lock_value))
    if not lock_acquired:
        logger.warning("同步任务已在执行中，跳过本次执行（可能是重复触发）")
        return
    
    try:
        db = SessionLocal()
        try:
            cluster_service = ClusterConfigService(db)
            snapshot_service = ResourceSnapshotService(db)
            asyncio.run(_sync_clusters_async(cluster_service, snapshot_service))
        finally:
            db.close()
    finally:
        # 释放锁（使用锁的值确保只有持有者才能释放）
        asyncio.run(cache_manager.release_lock(lock_key, value=lock_value))


@celery_app.task(
    name="app.tasks.observability_tasks.health_check_clusters",
    priority=settings.CELERY_TASK_PRIORITY_OBSERVABILITY,
    ignore_result=True,  # 忽略结果，避免存储任务结果
)
def health_check_clusters() -> None:
    """定时执行集群健康检查。"""
    if not settings.OBSERVABILITY_ENABLE_SCHEDULE:
        return
    db = SessionLocal()
    try:
        cluster_service = ClusterConfigService(db)
        asyncio.run(_health_check_async(cluster_service))
    finally:
        db.close()


async def _continue_diagnosis_async(db_session, record_id: int) -> None:
    service = DiagnosisService(db_session)
    await service.continue_diagnosis(record_id)


@celery_app.task(name="app.tasks.observability_tasks.continue_diagnosis")
def continue_diagnosis(record_id: int) -> None:
    """继续执行诊断迭代。"""
    if not settings.OBSERVABILITY_ENABLE_SCHEDULE:
        return
    db = SessionLocal()
    try:
        asyncio.run(_continue_diagnosis_async(db, record_id))
    finally:
        db.close()
