"""
Knowledge Base Schemas
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.base import BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema

class KnowledgeBaseCreate(BaseCreateSchema):
    """知识库创建模式"""
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    # 允许前端直接输入分类名；若提供则后端自动创建或复用
    category_name: Optional[str] = None

class KnowledgeBaseUpdate(BaseUpdateSchema):
    """知识库更新模式"""
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    is_active: Optional[bool] = None

class KnowledgeBaseResponse(BaseResponseSchema):
    """知识库响应模式"""
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    is_active: bool = True

class KnowledgeBaseListResponse(BaseModel):
    """知识库分页列表响应"""
    list: List[KnowledgeBaseResponse]
    total: int
    page: int
    size: int
