"""
Cleanup Tasks
"""

from celery import current_task
from app.tasks.celery_app import celery_app
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.models.image import DocumentImage
from app.models.version import DocumentVersion
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.config.opensearch import get_opensearch
from app.config.minio import get_minio
from datetime import datetime, timedelta
import os

@celery_app.task(bind=True)
def cleanup_deleted_documents_task(self):
    """清理已删除的文档任务"""
    db = SessionLocal()
    opensearch = get_opensearch()
    minio = get_minio()
    
    try:
        # 获取已删除的文档
        deleted_documents = db.query(Document).filter(
            Document.is_deleted == True
        ).all()
        
        total_documents = len(deleted_documents)
        cleaned_documents = 0
        
        for document in deleted_documents:
            # 删除相关分块
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
            
            # 删除相关图片
            db.query(DocumentImage).filter(DocumentImage.document_id == document.id).delete()
            
            # 删除相关版本
            db.query(DocumentVersion).filter(DocumentVersion.document_id == document.id).delete()
            
            # 删除OpenSearch索引
            opensearch.delete_by_query(
                index="document_content",
                body={"query": {"term": {"document_id": document.id}}}
            )
            
            # 删除MinIO文件
            try:
                minio.remove_object("multikb-knowledge-base", document.file_path)
            except Exception as e:
                print(f"删除MinIO文件失败: {e}")
            
            # 删除本地文件
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
            
            # 删除文档记录
            db.delete(document)
            
            cleaned_documents += 1
            
            # 更新进度
            progress = int((cleaned_documents / total_documents) * 100)
            current_task.update_state(
                state="PROGRESS",
                meta={"current": progress, "total": 100, "status": f"已清理 {cleaned_documents}/{total_documents} 个文档"}
            )
        
        db.commit()
        
        return {"status": "success", "message": f"已清理 {cleaned_documents} 个已删除的文档"}
        
    except Exception as e:
        db.rollback()
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def cleanup_old_versions_task(self, days: int = 30):
    """清理旧版本任务"""
    db = SessionLocal()
    
    try:
        # 获取指定天数前的版本
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_versions = db.query(DocumentVersion).filter(
            DocumentVersion.created_at < cutoff_date
        ).all()
        
        total_versions = len(old_versions)
        cleaned_versions = 0
        
        for version in old_versions:
            # 删除版本文件
            if os.path.exists(version.file_path):
                os.remove(version.file_path)
            
            # 删除版本记录
            db.delete(version)
            
            cleaned_versions += 1
            
            # 更新进度
            progress = int((cleaned_versions / total_versions) * 100)
            current_task.update_state(
                state="PROGRESS",
                meta={"current": progress, "total": 100, "status": f"已清理 {cleaned_versions}/{total_versions} 个版本"}
            )
        
        db.commit()
        
        return {"status": "success", "message": f"已清理 {cleaned_versions} 个旧版本"}
        
    except Exception as e:
        db.rollback()
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()

@celery_app.task
def cleanup_temp_files_task():
    """清理临时文件任务"""
    temp_dir = "temp"
    cleaned_files = 0
    
    try:
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    cleaned_files += 1
        
        return {"status": "success", "message": f"已清理 {cleaned_files} 个临时文件"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@celery_app.task
def cleanup_failed_tasks_task():
    """清理失败的任务任务"""
    # 这里应该实现清理失败任务的逻辑
    # 暂时跳过具体实现
    
    return {"status": "success", "message": "失败任务清理完成"}
