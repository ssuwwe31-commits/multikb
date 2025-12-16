"""
Chunk Service
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.chunk import DocumentChunk
from app.schemas.chunk import ChunkResponse
from app.services.base import BaseService

class ChunkService(BaseService[DocumentChunk]):
    """文档分块服务"""
    
    def __init__(self, db: Session):
        super().__init__(db, DocumentChunk)
    
    async def get_chunks(
        self, 
        skip: int = 0, 
        limit: int = 100,
        document_id: Optional[int] = None
    ) -> List[DocumentChunk]:
        """获取文档分块列表"""
        filters = {}
        if document_id:
            filters["document_id"] = document_id
        
        return await self.get_multi(skip=skip, limit=limit, **filters)
    
    async def get_chunk(self, chunk_id: int) -> Optional[DocumentChunk]:
        """获取文档分块详情"""
        return await self.get(chunk_id)
