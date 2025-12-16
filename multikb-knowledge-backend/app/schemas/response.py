"""
Response Schemas
"""

from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime

class SuccessResponse(BaseModel):
    """成功响应模式"""
    success: bool = True
    message: str
    data: Optional[Any] = None
    timestamp: datetime = datetime.now()

class ErrorResponse(BaseModel):
    """错误响应模式"""
    success: bool = False
    error: bool = True
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()

class PaginatedResponse(BaseModel):
    """分页响应模式"""
    items: list
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool
