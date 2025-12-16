"""
Batch Upload Service
批量上传服务 - 根据设计文档实现
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.batch import DocumentUploadBatch
from app.models.document import Document
from app.services.base import BaseService
from app.core.logging import logger
import json

class BatchService(BaseService[DocumentUploadBatch]):
    """批量上传服务"""
    
    def __init__(self, db: Session):
        super().__init__(db, DocumentUploadBatch)
    
    def create_batch(
        self,
        user_id: Optional[int],
        knowledge_base_id: int,
        total_files: int
    ) -> DocumentUploadBatch:
        """创建批次"""
        batch = DocumentUploadBatch(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            total_files=total_files,
            processed_files=0,
            success_files=0,
            failed_files=0,
            status="pending"
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        logger.info(f"创建批次: batch_id={batch.id}, total_files={total_files}")
        return batch
    
    def update_batch_progress(
        self,
        batch_id: int,
        success: bool = False,
        failed: bool = False
    ) -> Optional[DocumentUploadBatch]:
        """更新批次进度"""
        batch = self.db.query(DocumentUploadBatch).filter(
            DocumentUploadBatch.id == batch_id,
            DocumentUploadBatch.is_deleted == False
        ).first()
        
        if not batch:
            return None
        
        if success:
            batch.success_files += 1
        if failed:
            batch.failed_files += 1
        
        batch.processed_files += 1
        
        # 更新批次状态
        if batch.processed_files >= batch.total_files:
            if batch.failed_files == 0:
                batch.status = "completed"
            elif batch.success_files > 0:
                batch.status = "completed_with_errors"
            else:
                batch.status = "failed"
        elif batch.processed_files > 0:
            batch.status = "processing"
        
        self.db.commit()
        self.db.refresh(batch)
        return batch
    
    def get_batch_status(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """获取批次状态（包含文件详情）"""
        batch = self.db.query(DocumentUploadBatch).filter(
            DocumentUploadBatch.id == batch_id,
            DocumentUploadBatch.is_deleted == False
        ).first()
        
        if not batch:
            return None
        
        # 获取批次中的所有文档
        documents = self.db.query(Document).filter(
            and_(
                Document.batch_id == batch_id,
                Document.is_deleted == False
            )
        ).all()
        
        files = []
        for doc in documents:
            files.append({
                "document_id": doc.id,
                "filename": doc.original_filename,
                "status": doc.status,
                "security_scan_status": doc.security_scan_status or "pending",
                "processing_progress": doc.processing_progress or 0.0,
                "error_message": doc.error_message
            })
        
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "total_files": batch.total_files,
            "processed_files": batch.processed_files,
            "success_files": batch.success_files,
            "failed_files": batch.failed_files,
            "files": files
        }
    
    def update_batch_error_summary(self, batch_id: int, error_summary: Dict[str, Any]):
        """更新批次错误摘要"""
        batch = self.db.query(DocumentUploadBatch).filter(
            DocumentUploadBatch.id == batch_id,
            DocumentUploadBatch.is_deleted == False
        ).first()
        
        if batch:
            batch.error_summary = json.dumps(error_summary, ensure_ascii=False)
            self.db.commit()
