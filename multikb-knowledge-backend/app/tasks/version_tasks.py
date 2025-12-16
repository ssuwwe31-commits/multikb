"""
Version Management Tasks
"""

from celery import current_task
from app.tasks.celery_app import celery_app
from app.models.version import DocumentVersion
from app.models.document import Document
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.utils.file_utils import get_file_hash, get_file_size
import shutil
import os

@celery_app.task(bind=True)
def create_version_task(self, document_id: int, version_type: str = "auto"):
    """创建版本任务"""
    db = SessionLocal()
    try:
        # 获取文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise Exception(f"文档 {document_id} 不存在")
        
        # 获取当前版本号
        last_version = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        version_number = (last_version.version_number + 1) if last_version else 1
        
        # 创建版本记录
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            version_type=version_type,
            file_path=document.file_path,
            file_size=get_file_size(document.file_path),
            file_hash=get_file_hash(document.file_path)
        )
        
        db.add(version)
        db.commit()
        
        return {"status": "success", "message": "版本创建完成", "version_id": version.id}
        
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
def restore_version_task(self, version_id: int):
    """恢复版本任务"""
    db = SessionLocal()
    try:
        # 获取版本
        version = db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()
        if not version:
            raise Exception(f"版本 {version_id} 不存在")
        
        # 获取文档
        document = db.query(Document).filter(Document.id == version.document_id).first()
        if not document:
            raise Exception(f"文档 {version.document_id} 不存在")
        
        # 备份当前文件
        backup_path = f"{document.file_path}.backup"
        shutil.copy2(document.file_path, backup_path)
        
        # 恢复版本文件
        shutil.copy2(version.file_path, document.file_path)
        
        # 更新文档信息
        document.file_size = version.file_size
        document.file_hash = version.file_hash
        db.commit()
        
        # 删除备份文件
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        return {"status": "success", "message": "版本恢复完成"}
        
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
def cleanup_old_versions_task(document_id: int, keep_versions: int = 5):
    """清理旧版本任务"""
    db = SessionLocal()
    try:
        # 获取文档的所有版本
        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).all()
        
        # 删除超出保留数量的版本
        versions_to_delete = versions[keep_versions:]
        
        for version in versions_to_delete:
            # 删除版本文件
            if os.path.exists(version.file_path):
                os.remove(version.file_path)
            
            # 删除版本记录
            db.delete(version)
        
        db.commit()
        
        return {"status": "success", "message": f"已清理 {len(versions_to_delete)} 个旧版本"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task
def batch_create_versions_task(document_ids: list):
    """批量创建版本任务"""
    for document_id in document_ids:
        create_version_task.delay(document_id)
    
    return {"status": "success", "message": f"已启动 {len(document_ids)} 个版本创建任务"}
