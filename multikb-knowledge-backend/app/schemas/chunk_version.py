"""
Chunk Version Schemas
根据文档修改功能设计实现块版本管理Schema
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.base import BaseResponseSchema

class ChunkVersionCreate(BaseModel):
    """创建块版本请求模型"""
    chunk_id: int = Field(..., description="块ID")
    content: str = Field(..., min_length=1, description="版本内容")
    metadata: Optional[str] = Field(None, description="版本元数据")
    modified_by: Optional[str] = Field(None, description="修改者")
    version_comment: Optional[str] = Field(None, description="版本注释")

class ChunkVersionUpdate(BaseModel):
    """更新块版本请求模型"""
    content: Optional[str] = Field(None, min_length=1, description="版本内容")
    metadata: Optional[str] = Field(None, description="版本元数据")
    version_comment: Optional[str] = Field(None, description="版本注释")

class ChunkVersionResponse(BaseResponseSchema):
    """块版本响应模型"""
    chunk_id: int
    version_number: int
    content: str
    # ✅ 从 ORM 中的字段名 `meta` 读取，避免与 SQLAlchemy Base.metadata 冲突
    metadata: Optional[str] = Field(
        default=None,
        description="版本元数据",
        validation_alias='meta',
        serialization_alias='meta',
    )
    modified_by: Optional[str] = None
    version_comment: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChunkVersionListResponse(BaseModel):
    """块版本列表响应模型"""
    chunk_id: int = Field(..., description="块ID")
    total_versions: int = Field(..., description="总版本数")
    versions: List[ChunkVersionResponse] = Field([], description="版本列表")

class ChunkRevertRequest(BaseModel):
    """块回退请求模型"""
    target_version: int = Field(..., description="目标版本号")
    revert_comment: Optional[str] = Field(None, description="回退说明")

class ChunkRevertResponse(BaseModel):
    """块回退响应模型"""
    chunk_id: int = Field(..., description="块ID")
    from_version: int = Field(..., description="原版本号")
    to_version: int = Field(..., description="目标版本号")
    task_id: str = Field(..., description="回退任务ID")
    message: str = Field(..., description="回退消息")
