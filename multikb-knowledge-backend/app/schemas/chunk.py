"""
Chunk Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.base import BaseResponseSchema

class ChunkResponse(BaseResponseSchema):
    """文档分块响应模式"""
    document_id: int
    content: str
    chunk_index: int
    chunk_type: str = "text"
    metadata: Optional[dict] = None
