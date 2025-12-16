"""
Tasks API Routes
失败任务重试中心 - 根据设计文档实现
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.services.failure_retry_service import FailureRetryService
from app.dependencies.database import get_db
from app.core.logging import logger

router = APIRouter()

class BatchRetryRequest(BaseModel):
    """批量重试请求"""
    task_ids: List[int]
    task_type: str  # "document" or "image"

@router.get("/failures")
async def get_failure_tasks(
    task_type: Optional[str] = Query(None, description="任务类型: document|image"),
    knowledge_base_id: Optional[int] = Query(None, description="知识库ID"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取失败任务列表 - 根据设计文档实现"""
    try:
        retry_service = FailureRetryService(db)
        result = retry_service.get_failure_tasks(
            task_type=task_type,
            knowledge_base_id=knowledge_base_id,
            page=page,
            size=size
        )
        
        return {
            "code": 0,
            "message": "ok",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取失败任务列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取失败任务列表失败: {str(e)}"
        )

@router.post("/failures/{task_id}/retry")
async def retry_task(
    task_id: int,
    task_type: str = Query(..., description="任务类型: document|image"),
    db: Session = Depends(get_db)
):
    """重试单个任务 - 根据设计文档实现"""
    try:
        retry_service = FailureRetryService(db)
        success = retry_service.retry_task(task_id, task_type)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重试任务失败"
            )
        
        return {
            "code": 0,
            "message": "ok",
            "data": {"task_id": task_id, "status": "success"}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重试任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重试任务失败: {str(e)}"
        )

@router.post("/failures/batch-retry")
async def batch_retry_tasks(
    request: BatchRetryRequest,
    db: Session = Depends(get_db)
):
    """批量重试任务 - 根据设计文档实现"""
    try:
        retry_service = FailureRetryService(db)
        result = retry_service.batch_retry_tasks(
            task_ids=request.task_ids,
            task_type=request.task_type
        )
        
        return {
            "code": 0,
            "message": "ok",
            "data": result
        }
    except Exception as e:
        logger.error(f"批量重试任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量重试任务失败: {str(e)}"
        )
