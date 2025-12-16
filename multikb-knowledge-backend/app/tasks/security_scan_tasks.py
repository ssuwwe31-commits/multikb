"""
Security Scan Tasks
安全扫描任务 - 根据设计文档实现专用扫描队列
"""

from celery import current_task
from app.tasks.celery_app import celery_app
from app.services.file_validation_service import FileValidationService
from app.services.minio_storage_service import MinioStorageService
from app.models.document import Document
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.core.logging import logger
from app.tasks.document_tasks import process_document_task
from app.config.settings import settings
from datetime import datetime
import io
from starlette.datastructures import UploadFile

@celery_app.task(bind=True, ignore_result=True)
def security_scan_document_task(self, document_id: int):
    """
    安全扫描文档任务 - 串行执行，避免ClamAV压力过大
    
    流程：
    1. 从MinIO下载文件
    2. 执行安全扫描
    3. 更新文档的security_scan_status
    4. 如果扫描通过（safe或skipped），触发process_document_task
    """
    db = SessionLocal()
    document = None
    task_id = self.request.id if self else "unknown"
    
    try:
        logger.info(f"[扫描任务ID: {task_id}] 开始安全扫描文档 {document_id}")
        
        # 获取文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"[扫描任务ID: {task_id}] 文档 {document_id} 不存在")
            raise Exception(f"文档 {document_id} 不存在")
        
        # 更新扫描状态为scanning
        document.security_scan_status = "scanning"
        db.commit()
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "开始安全扫描"}
        )
        
        # 从MinIO下载文件
        logger.info(f"[扫描任务ID: {task_id}] 从MinIO下载文件: {document.file_path}")
        minio_service = MinioStorageService()
        file_content = minio_service.download_file(document.file_path)
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 30, "total": 100, "status": "执行安全扫描"}
        )
        
        # 创建UploadFile对象用于扫描
        file_io = io.BytesIO(file_content)
        upload_file = UploadFile(
            filename=document.original_filename,
            file=file_io,
            size=len(file_content)
        )
        
        # 执行安全扫描
        file_validation = FileValidationService()
        validation_result = file_validation.validate_file(upload_file)
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 80, "total": 100, "status": "更新扫描结果"}
        )
        
        # 提取安全扫描结果
        security_scan = validation_result.get("security_scan", {})
        security_scan_status = security_scan.get("scan_status", "pending")
        security_scan_method = security_scan.get("scan_method", "none")
        security_scan_result = {
            "virus_scan": security_scan.get("virus_scan"),
            "script_scan": security_scan.get("script_scan"),
            "threats_found": security_scan.get("threats_found", []),
            "scan_timestamp": datetime.utcnow().isoformat()
        }
        
        # 更新文档扫描结果
        document.security_scan_status = security_scan_status
        document.security_scan_method = security_scan_method
        document.security_scan_result = security_scan_result
        document.security_scan_timestamp = datetime.utcnow()
        db.commit()
        
        logger.info(f"[扫描任务ID: {task_id}] 安全扫描完成: status={security_scan_status}, method={security_scan_method}")
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 100, "total": 100, "status": "扫描完成"}
        )
        
        # 如果扫描通过（safe或skipped），触发文档处理任务
        if security_scan_status in ("safe", "skipped"):
            logger.info(f"[扫描任务ID: {task_id}] 扫描通过，触发文档处理任务")
            process_document_task.apply_async(
                args=(document_id,),
                queue="document",
                priority=settings.CELERY_TASK_PRIORITY_DOCUMENT
            )
        else:
            logger.warning(f"[扫描任务ID: {task_id}] 扫描未通过（status={security_scan_status}），不触发文档处理")
        
        current_task.update_state(
            state="SUCCESS",
            meta={"current": 100, "total": 100, "status": "扫描任务完成"}
        )
        
    except Exception as e:
        logger.error(f"[扫描任务ID: {task_id}] 安全扫描失败: {e}", exc_info=True)
        
        if document:
            try:
                document.security_scan_status = "error"
                document.security_scan_result = {
                    "error": str(e),
                    "scan_timestamp": datetime.utcnow().isoformat()
                }
                db.commit()
            except Exception:
                pass
        
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()
