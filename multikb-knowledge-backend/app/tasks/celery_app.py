"""
Celery App Configuration
"""

from celery import Celery
from app.config.settings import settings
from app.core.logging import logger

# 创建Celery应用
celery_app = Celery(
    "multikb-knowledge-backend",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.vector_tasks",
        "app.tasks.index_tasks",
        "app.tasks.image_tasks",
        "app.tasks.version_tasks",
        "app.tasks.cleanup_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.observability_tasks",
        "app.tasks.security_scan_tasks",
        "app.tasks.knowledge_graph_tasks",
    ]
)

# 输出 Redis 连接信息（仅在 Celery Worker/Beat 环境中打印）
def _is_celery_environment():
    """检查是否在 Celery Worker/Beat 环境中运行"""
    try:
        import sys
        import os
        # 方法1: 检查命令行参数（最可靠）
        if any("celery" in arg.lower() and ("worker" in arg.lower() or "beat" in arg.lower()) for arg in sys.argv):
            return True
        # 方法2: 检查环境变量（celery_worker/app.py 会设置）
        if os.getenv("CELERY_AUTOSTART", "").lower() == "true":
            return True
        # 方法3: 检查是否导入了 celery_worker 模块
        if "celery_worker" in sys.modules:
            return True
        return False
    except Exception:
        return False

try:
    if _is_celery_environment():
        logger.info(f"Celery 配置: broker={settings.REDIS_URL}, backend={settings.REDIS_URL}")
except Exception:
    pass

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟
    task_soft_time_limit=25 * 60,  # 25分钟
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # 任务确认机制：任务完成后才确认，防止重复执行
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 启动阶段无法连接到 broker 时立即失败（不重试），便于显式暴露配置/网络错误
    broker_connection_retry_on_startup=False,
    task_routes={
        "app.tasks.document_tasks.*": {"queue": "document"},
        "app.tasks.vector_tasks.*": {"queue": "vector"},
        "app.tasks.index_tasks.*": {"queue": "index"},
        "app.tasks.image_tasks.*": {"queue": "image"},
        "app.tasks.version_tasks.*": {"queue": "version"},
        "app.tasks.cleanup_tasks.*": {"queue": "cleanup"},
        "app.tasks.notification_tasks.*": {"queue": "notification"},
        "app.tasks.observability_tasks.*": {"queue": "observability"},
        "app.tasks.security_scan_tasks.*": {"queue": "security_scan"},
    },
    # 任务默认优先级：数字越大优先级越高（0-255）
    # 注意：优先级需要在任务发送时通过 priority 参数设置，这里只是默认值
    task_default_priority=settings.CELERY_TASK_PRIORITY_DEFAULT,
)

# 配置 Celery Beat 定时任务
celery_app.conf.beat_schedule = getattr(celery_app.conf, "beat_schedule", {})

# 清除旧的 observability 任务（如果存在），确保配置更新生效
if "observability-resource-sync" in celery_app.conf.beat_schedule:
    del celery_app.conf.beat_schedule["observability-resource-sync"]
if "observability-health-check" in celery_app.conf.beat_schedule:
    del celery_app.conf.beat_schedule["observability-health-check"]

# 根据配置决定是否启用 k8s 同步任务
if settings.OBSERVABILITY_ENABLE_SCHEDULE:
    celery_app.conf.beat_schedule.update(
        {
            "observability-resource-sync": {
                "task": "app.tasks.observability_tasks.sync_active_clusters",
                "schedule": settings.OBSERVABILITY_SYNC_INTERVAL_SECONDS,
                "options": {
                    "expires": settings.OBSERVABILITY_SYNC_INTERVAL_SECONDS,  # 任务过期时间，防止重复执行
                },
            },
            "observability-health-check": {
                "task": "app.tasks.observability_tasks.health_check_clusters",
                "schedule": settings.OBSERVABILITY_HEALTHCHECK_INTERVAL_SECONDS,
                "options": {
                    "expires": settings.OBSERVABILITY_HEALTHCHECK_INTERVAL_SECONDS,  # 任务过期时间，防止重复执行
                },
            },
        }
    )

# 根据配置决定是否启用自动重试任务
if getattr(settings, 'ENABLE_AUTO_RETRY', False):
    auto_retry_interval = getattr(settings, 'AUTO_RETRY_INTERVAL_SECONDS', 300)
    celery_app.conf.beat_schedule.update(
        {
            "auto-retry-failed-tasks": {
                "task": "app.tasks.auto_retry_tasks.auto_retry_failed_tasks_task",
                "schedule": auto_retry_interval,  # 使用重试间隔作为定时任务间隔
                "options": {
                    "expires": auto_retry_interval,
                },
            },
        }
    )
    try:
        if _is_celery_environment():
            logger.info(f"✅ Celery Beat 已启用自动重试任务: 间隔={auto_retry_interval}秒 ({auto_retry_interval/60:.1f}分钟)")
    except Exception:
        pass
    # 仅在 Celery Worker/Beat 环境中打印日志
    try:
        if _is_celery_environment():
            logger.info(
                f"✅ Celery Beat 已启用 k8s 同步任务: "
                f"同步间隔={settings.OBSERVABILITY_SYNC_INTERVAL_SECONDS}秒 ({settings.OBSERVABILITY_SYNC_INTERVAL_SECONDS/60:.1f}分钟), "
                f"健康检查间隔={settings.OBSERVABILITY_HEALTHCHECK_INTERVAL_SECONDS}秒 ({settings.OBSERVABILITY_HEALTHCHECK_INTERVAL_SECONDS/60:.1f}分钟)"
            )
    except Exception:
        pass
else:
    # 仅在 Celery Worker/Beat 环境中打印日志
    try:
        if _is_celery_environment():
            logger.info("❌ Celery Beat: OBSERVABILITY_ENABLE_SCHEDULE=False，已禁用 k8s 同步任务")
            logger.info("   提示: 如需启用，请在 .env 文件中设置 OBSERVABILITY_ENABLE_SCHEDULE=true 并重启 Celery Beat")
    except Exception:
        pass
