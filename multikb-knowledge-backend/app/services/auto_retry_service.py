"""
Auto Retry Service
自动重试服务 - 根据设计文档实现自动重试策略
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document import Document
from app.models.image import DocumentImage
from app.services.document_service import DocumentService
from app.services.image_service import ImageService
from app.core.logging import logger
from app.config.settings import settings
from datetime import datetime, timedelta

class AutoRetryService:
    """自动重试服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.document_service = DocumentService(db)
        self.image_service = ImageService(db)
    
    def should_auto_retry(self, task_type: str, retry_count: int, last_processed_at: Optional[datetime]) -> bool:
        """判断是否应该自动重试"""
        # 获取配置
        max_retries = getattr(settings, 'AUTO_RETRY_MAX_RETRIES', 3)
        retry_interval = getattr(settings, 'AUTO_RETRY_INTERVAL_SECONDS', 300)  # 默认5分钟
        
        # 检查重试次数
        if retry_count >= max_retries:
            logger.debug(f"任务已达到最大重试次数: {retry_count} >= {max_retries}")
            return False
        
        # 检查重试间隔
        if last_processed_at:
            time_since_last = datetime.utcnow() - last_processed_at.replace(tzinfo=None) if last_processed_at.tzinfo else datetime.utcnow() - last_processed_at
            if time_since_last.total_seconds() < retry_interval:
                logger.debug(f"距离上次处理时间过短: {time_since_last.total_seconds()} < {retry_interval}")
                return False
        
        return True
    
    def auto_retry_failed_tasks(self) -> Dict[str, Any]:
        """自动重试失败任务"""
        if not getattr(settings, 'ENABLE_AUTO_RETRY', False):
            logger.debug("自动重试功能未启用")
            return {"retried": 0, "skipped": 0}
        
        retried_count = 0
        skipped_count = 0
        
        # 获取失败任务（使用视图）
        query = """
            SELECT * FROM v_failure_tasks 
            WHERE retry_count < :max_retries
            ORDER BY last_processed_at ASC
            LIMIT :limit
        """
        max_retries = getattr(settings, 'AUTO_RETRY_MAX_RETRIES', 3)
        limit = getattr(settings, 'AUTO_RETRY_BATCH_SIZE', 10)
        
        result = self.db.execute(text(query), {
            "max_retries": max_retries,
            "limit": limit
        })
        
        tasks = []
        for row in result:
            tasks.append({
                "id": row.id,
                "task_type": row.task_type,
                "filename": row.filename,
                "retry_count": row.retry_count,
                "last_processed_at": row.last_processed_at
            })
        
        # 处理每个任务
        for task in tasks:
            try:
                # 判断是否应该重试
                if not self.should_auto_retry(
                    task["task_type"],
                    task["retry_count"],
                    task["last_processed_at"]
                ):
                    skipped_count += 1
                    continue
                
                # 执行重试
                logger.info(f"自动重试任务: task_id={task['id']}, task_type={task['task_type']}, retry_count={task['retry_count']}")
                
                if task["task_type"] == "document":
                    document = self.db.query(Document).filter(
                        Document.id == task["id"],
                        Document.is_deleted == False
                    ).first()
                    if document:
                        document.retry_count = (document.retry_count or 0) + 1
                        self.db.commit()
                        self.document_service.reprocess_document(task["id"])
                        retried_count += 1
                        logger.info(f"自动重试文档任务成功: document_id={task['id']}")
                
                elif task["task_type"] == "image":
                    image = self.db.query(DocumentImage).filter(
                        DocumentImage.id == task["id"],
                        DocumentImage.is_deleted == False
                    ).first()
                    if image:
                        image.retry_count = (image.retry_count or 0) + 1
                        self.db.commit()
                        self.image_service.process_image_sync(task["id"])
                        retried_count += 1
                        logger.info(f"自动重试图片任务成功: image_id={task['id']}")
                
            except Exception as e:
                logger.error(f"自动重试任务失败: task_id={task['id']}, error={e}", exc_info=True)
                skipped_count += 1
        
        logger.info(f"自动重试完成: 重试={retried_count}, 跳过={skipped_count}")
        return {
            "retried": retried_count,
            "skipped": skipped_count,
            "total": len(tasks)
        }
