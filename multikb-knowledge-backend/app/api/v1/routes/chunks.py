"""
Chunk API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.schemas.chunk import ChunkResponse
from app.services.chunk_service import ChunkService
from app.dependencies.database import get_db
from app.config.settings import settings
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/", response_model=List[ChunkResponse])
async def get_chunks(
    skip: int = 0,
    limit: int = settings.QA_DEFAULT_PAGE_SIZE,
    document_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取文档分块列表"""
    service = ChunkService(db)
    return await service.get_chunks(
        skip=skip, 
        limit=limit, 
        document_id=document_id
    )

@router.get("/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    chunk_id: int,
    db: Session = Depends(get_db)
):
    """获取文档分块详情"""
    service = ChunkService(db)
    chunk = await service.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档分块不存在"
        )
    return chunk
