"""
Failure Retry Service
失败重试服务 - 根据设计文档实现
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document import Document
from app.models.image import DocumentImage
from app.services.document_service import DocumentService
from app.services.image_service import ImageService
from app.core.logging import logger

class FailureRetryService:
    """失败重试服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.document_service = DocumentService(db)
        self.image_service = ImageService(db)
    
    def get_failure_tasks(
        self,
        task_type: Optional[str] = None,
        knowledge_base_id: Optional[int] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """获取失败任务列表（使用视图）"""
        skip = (page - 1) * size
        
        # 构建查询
        query = "SELECT * FROM v_failure_tasks WHERE 1=1"
        params = {}
        
        if task_type:
            query += " AND task_type = :task_type"
            params["task_type"] = task_type
        
        if knowledge_base_id:
            query += " AND knowledge_base_id = :knowledge_base_id"
            params["knowledge_base_id"] = knowledge_base_id
        
        query += " ORDER BY last_processed_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = size
        params["offset"] = skip
        
        # 执行查询
        result = self.db.execute(text(query), params)
        tasks = []
        for row in result:
            tasks.append({
                "id": row.id,
                "task_type": row.task_type,
                "filename": row.filename,
                "status": row.status,
                "error_message": row.error_message,
                "last_processed_at": row.last_processed_at.isoformat() if row.last_processed_at else None,
                "knowledge_base_id": row.knowledge_base_id,
                "user_id": row.user_id,
                "retry_count": row.retry_count,
                "document_id": row.document_id
            })
        
        # 获取总数
        count_query = "SELECT COUNT(*) as total FROM v_failure_tasks WHERE 1=1"
        count_params = {}
        if task_type:
            count_query += " AND task_type = :task_type"
            count_params["task_type"] = task_type
        if knowledge_base_id:
            count_query += " AND knowledge_base_id = :knowledge_base_id"
            count_params["knowledge_base_id"] = knowledge_base_id
        
        total_result = self.db.execute(text(count_query), count_params)
        total = total_result.scalar() or 0
        
        return {
            "tasks": tasks,
            "total": total,
            "page": page,
            "size": size
        }
    
    def retry_task(self, task_id: int, task_type: str) -> bool:
        """重试单个任务"""
        try:
            if task_type == "document":
                # 重试文档处理
                document = self.db.query(Document).filter(
                    Document.id == task_id,
                    Document.is_deleted == False
                ).first()
                
                if not document:
                    logger.error(f"文档不存在: {task_id}")
                    return False
                
                # 更新重试次数
                document.retry_count = (document.retry_count or 0) + 1
                self.db.commit()
                
                # 调用重试方法
                success = self.document_service.reprocess_document(task_id)
                logger.info(f"文档重试: document_id={task_id}, success={success}")
                return success
                
            elif task_type == "image":
                # 重试图片OCR
                image = self.db.query(DocumentImage).filter(
                    DocumentImage.id == task_id,
                    DocumentImage.is_deleted == False
                ).first()
                
                if not image:
                    logger.error(f"图片不存在: {task_id}")
                    return False
                
                # 更新重试次数
                image.retry_count = (image.retry_count or 0) + 1
                self.db.commit()
                
                # 调用重试方法
                success = self.image_service.process_image_sync(task_id)
                logger.info(f"图片OCR重试: image_id={task_id}, success={success}")
                return success
            else:
                logger.error(f"未知任务类型: {task_type}")
                return False
                
        except Exception as e:
            logger.error(f"重试任务失败: task_id={task_id}, task_type={task_type}, error={e}", exc_info=True)
            self.db.rollback()
            return False
    
    def batch_retry_tasks(self, task_ids: List[int], task_type: str) -> Dict[str, Any]:
        """批量重试任务"""
        success_count = 0
        failed_count = 0
        results = []
        
        for task_id in task_ids:
            try:
                success = self.retry_task(task_id, task_type)
                if success:
                    success_count += 1
                    results.append({"task_id": task_id, "status": "success"})
                else:
                    failed_count += 1
                    results.append({"task_id": task_id, "status": "failed", "error": "重试失败"})
            except Exception as e:
                failed_count += 1
                results.append({"task_id": task_id, "status": "failed", "error": str(e)})
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(task_ids),
            "results": results
        }
