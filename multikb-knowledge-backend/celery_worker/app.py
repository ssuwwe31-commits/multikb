"""
FastAPI entry for the Celery Worker Service.

- Health endpoints to verify environment and Redis connectivity
- Shares configuration with the main backend via `app.config.settings`
- Auto-start Celery worker and beat in background when running `python app.py`
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager

# Ensure project root is on sys.path when running from celery_worker directory
import os
import sys
import subprocess
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.config.settings import settings
from app.core.logging import logger

_worker_proc = None  # 全局保存 Worker 子进程句柄，便于优雅退出
_beat_proc = None  # 全局保存 Beat 子进程句柄，便于优雅退出
_beat_lock_value = None  # Beat 锁的值，用于释放锁
_beat_lock_key = None  # Beat 锁的 key


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 可在此添加更多启动检查（如 Redis/MinIO/OpenSearch）
    try:
        logger.info(f"Celery Health Service 使用 Redis: {settings.REDIS_URL}")
    except Exception:
        pass

    global _worker_proc, _beat_proc, _beat_lock_value, _beat_lock_key
    # 可通过环境变量关闭自动启动（默认开启）
    if os.getenv("CELERY_AUTOSTART", "true").lower() == "true":
        try:
            # 优先使用 settings 中的配置，如果没有则使用环境变量，最后使用默认值
            log_level = settings.CELERY_LOG_LEVEL or os.getenv("CELERY_LOG_LEVEL", "INFO")
            
            # 队列配置：优先使用 settings，然后环境变量，最后根据 OBSERVABILITY_ENABLE_SCHEDULE 决定
            if settings.CELERY_QUEUES:
                queues = settings.CELERY_QUEUES
            elif os.getenv("CELERY_QUEUES"):
                queues = os.getenv("CELERY_QUEUES")
            else:
                # 根据 OBSERVABILITY_ENABLE_SCHEDULE 决定默认队列
                if settings.OBSERVABILITY_ENABLE_SCHEDULE:
                    queues = "document,vector,index,image,version,cleanup,notification,observability,security_scan,celery"
                else:
                    queues = "document,vector,index,image,version,cleanup,notification,security_scan,celery"
                    logger.info("OBSERVABILITY_ENABLE_SCHEDULE=False，默认排除 observability 队列")
            
            # 并发数配置：优先使用 settings，然后环境变量，最后自动计算
            if settings.CELERY_CONCURRENCY is not None:
                concurrency = str(settings.CELERY_CONCURRENCY)
            elif os.getenv("CELERY_CONCURRENCY"):
                concurrency = os.getenv("CELERY_CONCURRENCY")
            else:
                # 自动计算并发数
                cpu_count = os.cpu_count() or 2
                # 默认取 [4, 8] 之间，确保有足够 worker 处理文档解析，即使 k8s 同步任务占用部分 worker
                # 如果 CPU 核心数 >= 4，使用 4-8 个并发；否则使用 2-4 个并发
                if cpu_count >= 4:
                    concurrency = str(max(4, min(8, cpu_count)))
                else:
                    concurrency = str(max(2, min(4, cpu_count)))
                logger.info(f"自动计算并发数: CPU核心数={cpu_count}, 并发数={concurrency} (考虑 k8s 同步任务占用)")
            
            logger.info(f"启动内嵌 Celery Worker(子进程): level={log_level}, queues={queues}, concurrency={concurrency}")

            # 以子进程方式启动 Worker，将工作目录设置为项目根，保证 `-m celery_worker.worker` 可导入
            env = {**os.environ, "CELERY_LOG_LEVEL": log_level, "CELERY_QUEUES": queues, "CELERY_CONCURRENCY": concurrency}
            _worker_proc = subprocess.Popen(
                [sys.executable, "-m", "celery_worker.worker"],
                cwd=_project_root,
                env=env,
            )
            
            # 启动 Celery Beat（定时任务调度器）
            if settings.OBSERVABILITY_ENABLE_SCHEDULE:
                # 使用 Redis 锁确保只有一个 Beat 实例在运行
                try:
                    from app.core.cache import cache_manager
                    import uuid
                    
                    beat_lock_key = "celery_beat_instance_lock"
                    beat_lock_value = str(uuid.uuid4())
                    beat_lock_timeout = 3600  # 1小时超时（如果 Beat 进程异常退出，锁会自动释放）
                    
                    # 尝试获取锁（在异步上下文中直接使用 await）
                    lock_acquired = await cache_manager.acquire_lock(
                        beat_lock_key, timeout=beat_lock_timeout, value=beat_lock_value
                    )
                    
                    if not lock_acquired:
                        logger.warning("检测到已有 Celery Beat 实例在运行（通过 Redis 锁），跳过启动新的 Beat 进程")
                        _beat_proc = None
                    else:
                        logger.info(f"启动内嵌 Celery Beat(子进程): level={log_level}, lock_value={beat_lock_value}")
                        _beat_proc = subprocess.Popen(
                            [sys.executable, "-m", "celery", "-A", "app.tasks.celery_app", "beat", "--loglevel", log_level.lower()],
                            cwd=_project_root,
                            env=env,
                        )
                        # 保存锁的值，用于后续释放
                        _beat_lock_value = beat_lock_value
                        _beat_lock_key = beat_lock_key
                except Exception as e:
                    logger.error(f"检查/启动 Beat 进程时出错: {e}，继续启动 Beat", exc_info=True)
                    # 如果锁机制失败，仍然启动 Beat（降级处理）
                    logger.info(f"启动内嵌 Celery Beat(子进程): level={log_level}")
                    _beat_proc = subprocess.Popen(
                        [sys.executable, "-m", "celery", "-A", "app.tasks.celery_app", "beat", "--loglevel", log_level.lower()],
                        cwd=_project_root,
                        env=env,
                    )
                    _beat_lock_value = None
                    _beat_lock_key = None
        except Exception as e:
            logger.error(f"内嵌 Celery Worker/Beat 启动失败: {e}", exc_info=True)

    try:
        yield
    finally:
        # 应用关闭时，优雅停止子进程
        if _beat_proc and _beat_proc.poll() is None:
            try:
                logger.info("正在终止内嵌 Celery Beat 子进程…")
                _beat_proc.terminate()
                _beat_proc.wait(timeout=10)
            except Exception:
                try:
                    logger.info("强制结束内嵌 Celery Beat 子进程…")
                    _beat_proc.kill()
                except Exception:
                    pass
        
        # 释放 Beat 锁
        if _beat_lock_key and _beat_lock_value:
            try:
                from app.core.cache import cache_manager
                await cache_manager.release_lock(_beat_lock_key, value=_beat_lock_value)
                logger.info("已释放 Celery Beat 实例锁")
            except Exception as e:
                logger.warning(f"释放 Beat 锁时出错: {e}")
        
        if _worker_proc and _worker_proc.poll() is None:
            try:
                logger.info("正在终止内嵌 Celery Worker 子进程…")
                _worker_proc.terminate()
                _worker_proc.wait(timeout=10)
            except Exception:
                try:
                    logger.info("强制结束内嵌 Celery Worker 子进程…")
                    _worker_proc.kill()
                except Exception:
                    pass


app = FastAPI(
    title="SPX Celery Worker",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {
        "service": "celery-worker",
        "status": "ok",
        "redis_url": settings.REDIS_URL,
    }


# 允许在该目录直接运行：python app.py
if __name__ == "__main__":
    import uvicorn
    # 作为独立健康检查服务运行，并自动在后台启动 Celery Worker（子进程）
    uvicorn.run("celery_worker.app:app", host="0.0.0.0", port=8010, reload=False)
