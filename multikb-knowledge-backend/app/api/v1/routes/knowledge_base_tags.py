"""
Knowledge Base Tags API Routes
根据文档处理流程设计实现知识库标签管理API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.core.logging import logger
from app.services.knowledge_base_tag_service import KnowledgeBaseTagService

router = APIRouter()

@router.get("/tags")
async def get_tags(
    page: int = 1,
    size: int = 20,
    tag_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取标签列表 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取标签列表，page: {page}, size: {size}, 类型: {tag_type}")
        
        service = KnowledgeBaseTagService(db)
        skip = max(page - 1, 0) * max(size, 1)
        result = service.get_tags(tag_type=tag_type, skip=skip, limit=size)
        
        total = result.get('total', len(result.get('tags', [])))
        logger.info(f"API响应: 返回 {len(result['tags'])} 个标签")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "list": result.get('tags', []),
                "total": total,
                "page": page,
                "size": size
            }
        }
        
    except Exception as e:
        logger.error(f"获取标签列表API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取标签列表失败: {str(e)}"
        )

@router.get("/tags/popular")
async def get_popular_tags(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取热门标签 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取热门标签，限制: {limit}")
        
        service = KnowledgeBaseTagService(db)
        tags = service.get_popular_tags(limit=limit)
        
        logger.info(f"API响应: 返回 {len(tags)} 个热门标签")
        return {"tags": tags}
        
    except Exception as e:
        logger.error(f"获取热门标签API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取热门标签失败: {str(e)}"
        )

@router.post("/documents/{document_id}/suggest-tags")
async def suggest_tags(
    document_id: int,
    db: Session = Depends(get_db)
):
    """推荐标签 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 为文档 {document_id} 推荐标签")
        
        service = KnowledgeBaseTagService(db)
        tags = service.suggest_tags(document_id)
        
        logger.info(f"API响应: 推荐了 {len(tags)} 个标签")
        return {"suggested_tags": tags}
        
    except Exception as e:
        logger.error(f"推荐标签API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推荐标签失败: {str(e)}"
        )

@router.post("/tags/batch-suggest")
async def batch_suggest_tags(
    document_ids: List[int],
    db: Session = Depends(get_db)
):
    """批量推荐标签 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 批量推荐标签，文档数量: {len(document_ids)}")
        
        service = KnowledgeBaseTagService(db)
        results = []
        
        for doc_id in document_ids:
            try:
                tags = service.suggest_tags(doc_id)
                results.append({
                    "document_id": doc_id,
                    "suggested_tags": tags,
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"文档 {doc_id} 标签推荐失败: {e}")
                results.append({
                    "document_id": doc_id,
                    "suggested_tags": [],
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"API响应: 批量推荐完成")
        return {"results": results}
        
    except Exception as e:
        logger.error(f"批量推荐标签API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量推荐标签失败: {str(e)}"
        )
