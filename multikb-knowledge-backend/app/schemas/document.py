"""
Document Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.base import BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema

class DocumentUploadRequest(BaseModel):
    """文档上传请求模式 - 根据设计文档实现"""
    knowledge_base_id: int = Field(..., description="知识库ID（必填）")
    category_id: Optional[int] = Field(None, description="分类ID（可选）")
    tags: Optional[List[str]] = Field(default=[], description="标签列表（可选）")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="可选元数据（JSON）")

class DocumentCreate(BaseCreateSchema):
    """文档创建模式"""
    original_filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    file_path: Optional[str] = None
    knowledge_base_id: int
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentUpdate(BaseUpdateSchema):
    """文档更新模式"""
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    file_path: Optional[str] = None
    knowledge_base_id: Optional[int] = None
    status: Optional[str] = None
    processing_progress: Optional[float] = None
    error_message: Optional[str] = None
    # 乐观并发控制字段：前端在更新时携带当前 known 的 updated_at，后端用于冲突检测
    expected_updated_at: Optional[datetime] = Field(
        default=None,
        description="期望的文档更新时间（用于乐观并发控制，不匹配则认为有并发修改）",
    )

class DocumentResponse(BaseResponseSchema):
    """文档响应模式"""
    original_filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    file_path: Optional[str] = None
    knowledge_base_id: int
    status: str = "uploaded"
    processing_progress: float = 0.0
    error_message: Optional[str] = None
    # 安全扫描字段
    security_scan_status: Optional[str] = "pending"
    security_scan_method: Optional[str] = None
    security_scan_result: Optional[Dict[str, Any]] = None
    security_scan_timestamp: Optional[datetime] = None
