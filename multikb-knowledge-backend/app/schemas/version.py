"""
Version Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.base import BaseResponseSchema

class VersionResponse(BaseResponseSchema):
    """版本响应模式"""
    document_id: int
    version_number: int
    version_type: str = "auto"  # auto, manual
    description: Optional[str] = None
    file_path: str
    file_size: int
    file_hash: str
