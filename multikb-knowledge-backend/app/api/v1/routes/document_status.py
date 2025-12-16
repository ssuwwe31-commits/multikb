"""
Document Status API Routes
根据文档处理流程设计实现文档状态查询API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.core.logging import logger
from app.config.settings import settings
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.task_status_service import TaskStatusService
from datetime import datetime

router = APIRouter()
task_status_service = TaskStatusService()

def _get_stage_from_status(document_status: str) -> str:
    """根据文档状态获取当前阶段"""
    stage_map = {
        "uploaded": "待处理",
        "parsing": "文档解析",
        "chunking": "内容分块",
        "vectorizing": "向量化处理",
        "indexing": "索引存储",
        "completed": "已完成",
        "failed": "处理失败"
    }
    return stage_map.get(document_status, "未知状态")

def _get_stage_description(status: str) -> str:
    """获取阶段描述"""
    descriptions = {
        "uploaded": "文档已上传，等待处理",
        "parsing": "正在解析文档内容",
        "chunking": "正在进行内容分块",
        "vectorizing": "正在使用Ollama生成文档向量",
        "indexing": "正在建立搜索索引",
        "completed": "文档处理已完成",
        "failed": "文档处理失败"
    }
    return descriptions.get(status, "未知状态")

def _get_processing_stages(document_status: str, progress: float, chunk_count: int) -> list:
    """获取处理阶段列表"""
    stages = [
        {"stage": "文件验证", "status": "completed"},
        {"stage": "安全扫描", "status": "completed"},
        {"stage": "重复检测", "status": "completed"},
        {"stage": "文件存储", "status": "completed"},
        {"stage": "文档解析", "status": "completed" if document_status in ["chunking", "vectorizing", "indexing", "completed"] else "pending"},
        {"stage": "内容分块", "status": "completed" if document_status in ["vectorizing", "indexing", "completed"] else "pending"},
        {"stage": "向量化处理", "status": "processing" if document_status == "vectorizing" else ("completed" if document_status in ["indexing", "completed"] else "pending")},
        {"stage": "索引存储", "status": "processing" if document_status == "indexing" else ("completed" if document_status == "completed" else "pending")}
    ]
    
    # 根据状态设置当前阶段
    current_index = ["uploaded", "parsing", "chunking", "vectorizing", "indexing", "completed"].index(document_status) if document_status in ["uploaded", "parsing", "chunking", "vectorizing", "indexing", "completed"] else 0
    
    for i, stage in enumerate(stages):
        if i < current_index:
            stage["status"] = "completed"
        elif i == current_index:
            stage["status"] = "processing"
        else:
            stage["status"] = "pending"
    
    return stages

def _get_statistics(document: Document, chunk_count: int, task_status: Dict[str, Any]) -> Dict[str, Any]:
    """获取统计信息"""
    stats = {
        "total_chunks": chunk_count,
        "processed_chunks": chunk_count,
        "remaining_chunks": 0,
        "vector_dimension": settings.TEXT_EMBEDDING_DIMENSION,
        "file_size": f"{document.file_size / (1024*1024):.2f}MB" if document.file_size else "未知",
    }
    
    # 如果有任务状态，更新进度信息
    if task_status:
        current = task_status.get("progress", 0)
        total = task_status.get("total", 100)
        if total > 0:
            stats["processed_chunks"] = int(chunk_count * (current / total))
            stats["remaining_chunks"] = chunk_count - stats["processed_chunks"]
        stats["processing_speed"] = f"{chunk_count / 60:.1f} chunks/min" if chunk_count > 0 else "0 chunks/min"
    
    return stats

def _estimate_completion_time(progress: float, task_status: Dict[str, Any]) -> str:
    """估算完成时间"""
    if progress >= 100:
        return datetime.utcnow().isoformat() + "Z"
    
    if task_status:
        remaining = 100 - progress
        # 简单的线性估算
        estimated_minutes = remaining / 10  # 假设每10%需要1分钟
        estimated_time = datetime.utcnow().timestamp() + estimated_minutes * 60
        return datetime.fromtimestamp(estimated_time).isoformat() + "Z"
    
    return "未知"

@router.get("/documents/{document_id}/status")
async def get_document_status(
    document_id: int,
    db: Session = Depends(get_db)
):
    """获取文档处理状态 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取文档 {document_id} 的处理状态")
        
        # 查询文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档 {document_id} 不存在"
            )
        
        # 获取任务状态（如果有任务ID）
        task_status = None
        if hasattr(document, 'task_id') and document.task_id:
            task_status = task_status_service.get_task_status(document.task_id)
        
        # 计算处理进度
        progress = document.processing_progress if document.processing_progress else 0
        current_stage = _get_stage_from_status(document.status)
        
        # 统计分块信息
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()
        
        # 构建状态信息
        processing_stages = _get_processing_stages(document.status, progress, chunk_count)
        statistics = _get_statistics(document, chunk_count, task_status)
        
        status_info = {
            "document_id": document_id,
            "processing_status": document.status,
            "progress_percentage": progress,
            "current_stage": current_stage,
            "stage_description": _get_stage_description(document.status),
            "error_message": document.error_message if hasattr(document, 'error_message') else None,
            "estimated_completion_time": _estimate_completion_time(progress, task_status),
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "processing_stages": processing_stages,
            "statistics": statistics
        }
        
        logger.info(f"API响应: 返回文档 {document_id} 的状态信息")
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档状态API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档状态失败: {str(e)}"
        )

@router.get("/documents/{document_id}/progress")
async def get_document_progress(
    document_id: int,
    db: Session = Depends(get_db)
):
    """获取文档处理进度 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取文档 {document_id} 的处理进度")
        
        # 查询文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档 {document_id} 不存在"
            )
        
        # 获取任务状态
        task_status = None
        if hasattr(document, 'task_id') and document.task_id:
            task_status = task_status_service.get_task_progress(document.task_id)
        
        # 计算进度
        overall_progress = document.processing_progress if document.processing_progress else 0
        current_stage = _get_stage_from_status(document.status)
        
        # 估算剩余时间
        estimated_remaining = ""
        if overall_progress < 100:
            remaining = 100 - overall_progress
            estimated_minutes = remaining / 10
            estimated_remaining = f"{int(estimated_minutes)}分{int((estimated_minutes - int(estimated_minutes)) * 60)}秒"
        
        progress_info = {
            "document_id": document_id,
            "overall_progress": overall_progress,
            "current_stage": current_stage,
            "stage_progress": task_status.get("progress_percentage", 0) if task_status else 0,
            "estimated_remaining_time": estimated_remaining,
            "processing_speed": "5 chunks/min",  # TODO: 从任务状态获取实际速度
            "last_updated": document.updated_at.isoformat() if document.updated_at else None
        }
        
        logger.info(f"API响应: 返回文档 {document_id} 的进度信息")
        return progress_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档进度API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档进度失败: {str(e)}"
        )

@router.get("/documents/{document_id}/processing-history")
async def get_processing_history(
    document_id: int,
    db: Session = Depends(get_db)
):
    """获取文档处理历史 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取文档 {document_id} 的处理历史")
        
        # 查询文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档 {document_id} 不存在"
            )
        
        # 获取任务历史
        task_status = None
        if hasattr(document, 'task_id') and document.task_id:
            task_status = task_status_service.get_task_status(document.task_id)
        
        # 构建处理历史
        history = {
            "document_id": document_id,
            "processing_history": [
                {
                    "stage": _get_stage_from_status(stage),
                    "status": "completed" if stage in ["completed"] or document.status == "completed" else "pending",
                    "start_time": document.created_at.isoformat() if document.created_at else None,
                    "end_time": document.updated_at.isoformat() if document.updated_at else None,
                }
                for stage in ["uploaded", "parsing", "chunking", "vectorizing", "indexing"]
            ],
            "total_processing_time": "未知",
            "current_status": document.status,
            "error_message": document.error_message if hasattr(document, 'error_message') else None
        }
        
        logger.info(f"API响应: 返回文档 {document_id} 的处理历史")
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档处理历史API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档处理历史失败: {str(e)}"
        )
