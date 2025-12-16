"""
Export API Routes
导出API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.services.export_service import ExportService
from app.dependencies.database import get_db
from app.core.logging import logger

router = APIRouter()

def get_current_user_id(request: Request) -> int:
    """从请求中获取当前用户ID（由中间件设置）"""
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户信息")
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户ID")

class KnowledgeBaseExportRequest(BaseModel):
    """知识库导出请求"""
    format: str = "markdown"  # markdown/pdf/json
    include_documents: bool = True
    include_chunks: bool = False

class DocumentExportRequest(BaseModel):
    """文档导出请求"""
    format: str = "markdown"  # markdown/pdf/json/original
    include_chunks: bool = True
    include_images: bool = False
    export_original: bool = False  # 是否导出原始文档（直接从MinIO获取）

class QAHistoryExportRequest(BaseModel):
    """问答历史导出请求"""
    format: str = "json"  # json/csv/markdown
    session_id: Optional[str] = None  # ✅ 支持字符串类型的session_id（UUID格式）
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class BatchDocumentExportRequest(BaseModel):
    """批量文档导出请求"""
    document_ids: list[int]
    format: str = "markdown"  # markdown/json
    include_chunks: bool = True
    include_images: bool = False

@router.post("/knowledge-bases/{kb_id}/export")
async def export_knowledge_base(
    kb_id: int,
    request: Request,
    export_request: KnowledgeBaseExportRequest,
    db: Session = Depends(get_db)
):
    """导出知识库"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 导出知识库，知识库ID: {kb_id}, 格式: {export_request.format}, 用户ID: {user_id}")
        
        service = ExportService(db)
        task = await service.export_knowledge_base(
            user_id=user_id,
            kb_id=kb_id,
            format=export_request.format,
            include_documents=export_request.include_documents,
            include_chunks=export_request.include_chunks
        )
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "task_id": task.id,
                "status": task.status,
                "estimated_time": 30  # 简化实现
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"导出知识库API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出知识库失败: {str(e)}"
        )

@router.post("/documents/{doc_id}/export")
async def export_document(
    doc_id: int,
    request: Request,
    export_request: DocumentExportRequest,
    db: Session = Depends(get_db)
):
    """导出文档"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 导出文档，文档ID: {doc_id}, 格式: {export_request.format}, 用户ID: {user_id}")
        
        service = ExportService(db)
        task = await service.export_document(
            user_id=user_id,
            doc_id=doc_id,
            format=export_request.format,
            include_chunks=export_request.include_chunks,
            include_images=export_request.include_images,
            export_original=export_request.export_original
        )
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "task_id": task.id,
                "status": task.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"导出文档API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出文档失败: {str(e)}"
        )

@router.post("/qa/history/export")
async def export_qa_history(
    request: Request,
    export_request: QAHistoryExportRequest,
    db: Session = Depends(get_db)
):
    """导出问答历史"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 导出问答历史，格式: {export_request.format}, 用户ID: {user_id}")
        
        service = ExportService(db)
        task = await service.export_qa_history(
            user_id=user_id,
            format=export_request.format,
            session_id=export_request.session_id,
            start_date=export_request.start_date,
            end_date=export_request.end_date
        )
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "task_id": task.id,
                "status": task.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"导出问答历史API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出问答历史失败: {str(e)}"
        )

@router.post("/documents/batch/export")
async def batch_export_documents(
    request: Request,
    export_request: BatchDocumentExportRequest,
    db: Session = Depends(get_db)
):
    """批量导出文档"""
    try:
        user_id = get_current_user_id(request)
        document_ids = export_request.document_ids
        
        logger.info(f"API请求: 批量导出文档，文档数量: {len(document_ids)}, 格式: {export_request.format}, 用户ID: {user_id}")
        
        if not document_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档ID列表不能为空")
        
        service = ExportService(db)
        tasks = []
        
        for doc_id in document_ids:
            try:
                task = await service.export_document(
                    user_id=user_id,
                    doc_id=doc_id,
                    format=export_request.format,
                    include_chunks=export_request.include_chunks,
                    include_images=export_request.include_images,
                    export_original=export_request.export_original if hasattr(export_request, 'export_original') else False
                )
                tasks.append({
                    "document_id": doc_id,
                    "task_id": task.id,
                    "status": task.status
                })
            except Exception as e:
                logger.error(f"导出文档 {doc_id} 失败: {e}")
                tasks.append({
                    "document_id": doc_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "tasks": tasks,
                "total": len(document_ids)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导出文档API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量导出文档失败: {str(e)}"
        )

@router.get("/")
async def get_export_tasks(
    request: Request,
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """获取导出任务列表"""
    try:
        user_id = get_current_user_id(request)
        logger.info(
            f"API请求: 获取导出任务列表, 用户ID: {user_id}, status: {status}, limit: {limit}, offset: {offset}"
        )
        service = ExportService(db)
        tasks = service.get_export_tasks(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # 为每个任务生成下载URL
        tasks_data = []
        for task in tasks:
            download_url = None
            if task.status == "completed" and task.file_path:
                download_url = await service.get_export_download_url(task.id, user_id)
            
            tasks_data.append({
                "task_id": task.id,
                "export_type": task.export_type,
                "export_format": task.export_format,
                "status": task.status,
                "file_path": task.file_path,
                "file_size": task.file_size,
                "download_url": download_url,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            })
        
        logger.info(
            f"API响应: 获取导出任务列表, 用户ID: {user_id}, 返回任务数: {len(tasks_data)}"
        )
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "list": tasks_data,
                "total": len(tasks_data)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取导出任务列表API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取导出任务列表失败: {str(e)}"
        )

@router.get("/{task_id}")
async def get_export_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """查询导出任务状态"""
    try:
        user_id = get_current_user_id(request)
        service = ExportService(db)
        task = service.get_export_task(task_id, user_id)
        
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出任务不存在")
        
        download_url = None
        if task.status == "completed" and task.file_path:
            download_url = await service.get_export_download_url(task_id, user_id)
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "task_id": task.id,
                "export_type": task.export_type,
                "export_format": task.export_format,
                "status": task.status,
                "file_path": task.file_path,
                "file_size": task.file_size,
                "download_url": download_url,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询导出任务API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询导出任务失败: {str(e)}"
        )

@router.delete("/{task_id}")
async def delete_export_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """删除导出任务（软删除+硬删除同时执行）"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 删除导出任务, task_id: {task_id}, 用户ID: {user_id}")
        service = ExportService(db)
        
        # 先检查任务是否存在
        task = service.get_export_task(task_id, user_id)
        if not task:
            # 尝试获取已删除的任务，用于错误提示
            task_all = service.db.query(ExportTask).filter(
                ExportTask.id == task_id,
                ExportTask.user_id == user_id
            ).first()
            if not task_all:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出任务不存在")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出任务已删除")
        
        # 执行删除（软删除+硬删除）
        success = service.delete_export_task(task_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除导出任务失败"
            )
        
        logger.info(f"API响应: 删除导出任务成功, task_id: {task_id}, 用户ID: {user_id}")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "task_id": task_id,
                "deleted": True
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除导出任务API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除导出任务失败: {str(e)}"
        )

@router.get("/{task_id}/download")
async def download_export_file(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """下载导出文件"""
    try:
        user_id = get_current_user_id(request)
        service = ExportService(db)
        task = service.get_export_task(task_id, user_id)
        
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出任务不存在")
        
        if task.status != "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="导出任务未完成")
        
        if not task.file_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出文件不存在")
        
        # 从MinIO下载文件
        file_data = service.minio.client.get_object(service.minio.bucket_name, task.file_path)
        content = file_data.read()
        
        # 确定Content-Type
        content_type = "application/octet-stream"
        if task.export_format == "json":
            content_type = "application/json"
        elif task.export_format == "markdown":
            content_type = "text/markdown"
        elif task.export_format == "csv":
            content_type = "text/csv"
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="export_{task_id}.{task.export_format}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载导出文件API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载导出文件失败: {str(e)}"
        )
