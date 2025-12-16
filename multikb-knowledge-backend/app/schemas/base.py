"""
Base Schema for Pydantic
"""

from pydantic import BaseModel as PydanticBaseModel
from datetime import datetime
from typing import Optional

class BaseSchema(PydanticBaseModel):
    """基础模式类"""
    class Config:
        from_attributes = True

class BaseCreateSchema(BaseSchema):
    """基础创建模式"""
    pass

class BaseUpdateSchema(BaseSchema):
    """基础更新模式"""
    pass

class BaseResponseSchema(BaseSchema):
    """基础响应模式"""
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
