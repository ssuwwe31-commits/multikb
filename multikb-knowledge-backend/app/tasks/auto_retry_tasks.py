"""
Auto Retry Tasks
自动重试任务 - 根据设计文档实现自动重试策略
"""

from app.tasks.celery_app import celery_app
from app.services.auto_retry_service import AutoRetryService
from app.config.database import SessionLocal
from app.core.logging import logger
from app.config.settings import settings

@celery_app.task(bind=True, ignore_result=True)
def auto_retry_failed_tasks_task(self):
    """自动重试失败任务（定时任务）"""
    db = SessionLocal()
    try:
        if not getattr(settings, 'ENABLE_AUTO_RETRY', False):
            logger.debug("自动重试功能未启用，跳过")
            return {"retried": 0, "skipped": 0}
        
        retry_service = AutoRetryService(db)
        result = retry_service.auto_retry_failed_tasks()
        
        logger.info(f"自动重试任务完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"自动重试任务执行失败: {e}", exc_info=True)
        raise e
    finally:
        db.close()
