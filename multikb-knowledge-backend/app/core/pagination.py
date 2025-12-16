"""
Pagination Module
"""

from typing import List, Optional, Any
from pydantic import BaseModel

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    size: int = 20
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.page < 1:
            self.page = 1
        if self.size < 1:
            self.size = 20
        if self.size > 100:
            self.size = 100

class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool

def paginate(
    items: List[Any], 
    total: int, 
    page: int, 
    size: int
) -> PaginatedResponse:
    """分页处理"""
    pages = (total + size - 1) // size
    has_next = page < pages
    has_prev = page > 1
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev
    )

def paginate_response(
    data: List[Any],
    total: int,
    page: int,
    size: int
) -> dict:
    """分页响应（返回字典格式，兼容FastAPI）"""
    pages = (total + size - 1) // size if size > 0 else 0
    has_next = page < pages
    has_prev = page > 1
    
    return {
        "list": data,  # 使用list作为键名，兼容前端
        "items": data,  # 同时提供items键名
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": has_next,
        "has_prev": has_prev
    }

def get_offset(page: int, size: int) -> int:
    """获取偏移量"""
    return (page - 1) * size
