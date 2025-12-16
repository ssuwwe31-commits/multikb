from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from app.config.database import SessionLocal
from sqlalchemy.orm import Session
from app.services.query_service import QueryService
from app.services.document_service import DocumentService
from app.models.image import DocumentImage
from app.core.logging import logger
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/query", tags=["query"], dependencies=[Depends(get_current_user)])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ContextResponse(BaseModel):
    data: Dict[str, Any]


@router.get("/documents/{document_id}/chunks/{chunk_id}/context", response_model=ContextResponse)
def get_chunk_context(
    document_id: int,
    chunk_id: int,
    neighbor_pre: int = 1,
    neighbor_next: int = 1,
    parent_group_max_chars: int = 1500,
    db: Session = Depends(get_db),
):
    service = QueryService(db)
    result = service.get_context_for_hit(
        document_id=document_id,
        hit_chunk_id=chunk_id,
        neighbor_pre=neighbor_pre,
        neighbor_next=neighbor_next,
        parent_group_max_chars=parent_group_max_chars,
    )
    if "error" in result:
        logger.warning(f"[QueryAPI] chunk-context not found: {result['error']}")
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}


@router.get("/documents/{document_id}/images/{image_id}/context", response_model=ContextResponse)
def get_image_context(
    document_id: int,
    image_id: int,
    neighbor_pre: int = 1,
    neighbor_next: int = 1,
    min_confidence: float = 0.5,
    rerank: bool = False,
    db: Session = Depends(get_db),
):
    """图片上下文：返回图片的位置信息与关联文本块（含前后邻居）。"""
    # 取图片
    image = db.query(DocumentImage).filter(
        DocumentImage.id == image_id,
        DocumentImage.document_id == document_id,
        DocumentImage.is_deleted == False,
    ).first()
    if not image:
        logger.warning("[QueryAPI] image-context: image_not_found")
        raise HTTPException(status_code=404, detail="image_not_found")

    # 关联文本块
    doc_service = DocumentService(db)
    associated = doc_service.get_chunks_for_image(
        document_id=document_id,
        image=image,
        min_confidence=min_confidence,
        return_with_confidence=True,
        use_rerank=rerank,
    )

    # 取每个关联块的上下文（可只取排名第一的块扩展上下文）
    qsvc = QueryService(db)
    contexts = []
    for idx, (chunk, conf) in enumerate(associated[:3]):
        ctx = qsvc.get_context_for_hit(
            document_id=document_id,
            hit_chunk_id=chunk.id,
            neighbor_pre=neighbor_pre,
            neighbor_next=neighbor_next,
        )
        contexts.append({"chunk_id": chunk.id, "confidence": conf, "context": ctx})

    # 位置/坐标元数据
    import json
    meta = {}
    if image.meta:
        try:
            meta = json.loads(image.meta) if isinstance(image.meta, str) else image.meta
        except Exception:
            meta = {}

    # 坐标统一化（0-1）
    coords = meta.get("coordinates") or {}
    try:
        from app.config.settings import settings as _settings
        if getattr(_settings, 'IMAGE_COORDS_NORMALIZE', True) and coords:
            w_ref = meta.get('width') or meta.get('page_width')
            h_ref = meta.get('height') or meta.get('page_height')
            x = coords.get('x', coords.get('left', 0.0))
            y = coords.get('y', coords.get('top', 0.0))
            w = coords.get('width', coords.get('w', 0.0))
            h = coords.get('height', coords.get('h', 0.0))
            if max(x + w, y + h, w, h) > 1.0 and w_ref and h_ref and w_ref > 0 and h_ref > 0:
                coords = {"x": x / w_ref, "y": y / h_ref, "width": w / w_ref, "height": h / h_ref}
    except Exception:
        pass
    position = {
        "page_number": meta.get("page_number"),
        "coordinates": coords,
        "element_index": meta.get("element_index"),
    }

    return {"data": {"image": {"image_id": image.id}, "position": position, "associations": contexts}}
