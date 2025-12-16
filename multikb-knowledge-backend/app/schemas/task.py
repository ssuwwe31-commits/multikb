"""
Task Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.base import BaseResponseSchema

class TaskResponse(BaseResponseSchema):
    """任务响应模式"""
    task_id: str
    task_name: str
    status: str = "pending"
    progress: float = 0.0
    result: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
