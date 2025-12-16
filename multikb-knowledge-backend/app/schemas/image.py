"""
Image Schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
import json
from datetime import datetime
from app.schemas.base import BaseResponseSchema
from app.schemas.image_search import ImageSearchRequest, ImageSearchResponse

class ImageResponse(BaseResponseSchema):
    """图片响应模式"""
    document_id: int
    image_path: str
    # 后端历史数据中可能为空，这里放宽为可选
    image_type: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    ocr_text: Optional[str] = None
    vector_model: Optional[str] = None
    vector_dim: Optional[int] = None
    status: Optional[str] = None
    retry_count: Optional[int] = None
    error_message: Optional[str] = None
    last_processed_at: Optional[datetime] = None
    # 模型字段名为 meta（列名为 metadata），需要别名映射
    metadata: Optional[dict] = Field(default=None, validation_alias='meta', serialization_alias='metadata')

    @field_validator('metadata', mode='before')
    @classmethod
    def _parse_metadata(cls, v: Any) -> Optional[dict]:
        # 支持 None / dict / JSON 字符串
        if v is None or isinstance(v, dict):
            return v
        if isinstance(v, (bytes, bytearray)):
            try:
                return json.loads(v.decode('utf-8'))
            except Exception:
                return None
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                return json.loads(v)
            except Exception:
                return None
        # 避免把 SQLAlchemy 的 MetaData 传出
        return None
