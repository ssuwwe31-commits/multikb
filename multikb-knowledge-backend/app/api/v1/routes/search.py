"""
Search API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import time
from app.schemas.search import (
    SearchRequest, SearchResponse, SearchSuggestionRequest,
    SearchHistoryResponse, SaveSearchRequest, SearchAdvancedRequest,
    SearchFacetsResponse, SimilarSearchRequest
)
from app.services.search_service import SearchService
from app.services.search_history_service import SearchHistoryService
from app.dependencies.database import get_db
from app.core.logging import logger
from app.config.settings import settings

router = APIRouter()

def get_current_user_id(request: Request) -> Optional[int]:
    """从请求中获取当前用户ID（由中间件设置）"""
    user = getattr(request.state, 'user', None)
    if not user:
        return None
    user_id = user.get("sub")
    if not user_id:
        return None
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return None


@router.get("/mixed")
async def mixed_search(
    q: str = Query(..., description="查询文本"),
    top_k: int = Query(None, ge=1, le=100, description="返回结果数量（如果为None，使用配置的RERANK_TOP_K）"),
    kb_id: int | None = Query(None, description="知识库ID"),
    alpha: float = Query(0.6, ge=0.0, le=1.0, description="向量搜索权重"),
    use_vector: bool = Query(True, description="是否使用向量搜索"),
    use_keywords: bool = Query(True, description="是否使用关键词搜索"),
    similarity_threshold: float | None = Query(None, ge=0.0, le=1.0, description="相似度阈值(0-1)"),
    db: Session = Depends(get_db),
):
    """混合搜索接口 - 支持向量+关键词融合检索+Rerank精排"""
    try:
        logger.info(f"API请求: 混合搜索(GET)，查询: {q[:50]}..., 知识库ID: {kb_id}, top_k: {top_k}, 阈值: {similarity_threshold}")
        svc = SearchService(db)
        items = await svc.mixed_search(
            query_text=q,
            knowledge_base_id=kb_id,
            top_k=top_k,
            alpha=alpha,
            use_keywords=use_keywords,
            use_vector=use_vector,
            similarity_threshold=similarity_threshold
        )
        logger.info(f"API响应: 返回 {len(items)} 个搜索结果")
        return {"code": 0, "message": "ok", "data": {"list": items, "total": len(items)}}
    except Exception as e:
        logger.error(f"混合搜索API错误(GET): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"混合搜索失败: {str(e)}"
        )

@router.post("/")
async def search(
    search_request: SearchRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """基础搜索 - 支持关键词、语义、混合搜索 + Rerank精排
    
    注意：知识库ID(knowledge_base_id)是可选参数，但如果提供，搜索结果将被限制在指定的知识库内。
    前端应该要求用户先选择知识库再进行搜索，以确保搜索结果的准确性。
    """
    start_time = time.time()
    try:
        logger.info(f"API请求: 文本搜索，查询: {search_request.query[:50]}..., 类型: {search_request.search_type}, 知识库ID: {search_request.knowledge_base_id}")
        
        # 验证知识库ID是否存在（如果提供了）
        if search_request.knowledge_base_id:
            from app.models.knowledge_base import KnowledgeBase
            kb_ids = search_request.knowledge_base_id
            if isinstance(kb_ids, list):
                if len(kb_ids) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="至少需要选择一个知识库"
                    )
                # 验证所有知识库ID是否存在且激活
                kbs = db.query(KnowledgeBase).filter(
                    KnowledgeBase.id.in_(kb_ids),
                    KnowledgeBase.is_active == True
                ).all()
                found_ids = {kb.id for kb in kbs}
                missing_ids = set(kb_ids) - found_ids
                if missing_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"以下知识库ID不存在或未激活: {', '.join(map(str, missing_ids))}"
                    )
            elif isinstance(kb_ids, int):
                kb = db.query(KnowledgeBase).filter(
                    KnowledgeBase.id == kb_ids,
                    KnowledgeBase.is_active == True
                ).first()
                if not kb:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"知识库ID {kb_ids} 不存在或未激活"
                    )
        
        service = SearchService(db)
        results = await service.search(search_request)
        
        # 计算搜索耗时
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # 自动保存搜索历史
        user_id = get_current_user_id(request)
        if user_id:
            try:
                history_service = SearchHistoryService(db)
                await history_service.save_search_history(
                    user_id=user_id,
                    query_text=search_request.query,
                    search_type=search_request.search_type,
                    knowledge_base_id=search_request.knowledge_base_id,
                    result_count=len(results),
                    search_time_ms=search_time_ms
                )
            except Exception as e:
                # 保存历史失败不影响搜索结果
                logger.warning(f"保存搜索历史失败: {e}")
        
        logger.info(f"API响应(HTTP): 最终返回前端 {len(results)} 个搜索结果（total={len(results)}, items={len(results)}），耗时: {search_time_ms}ms")
        return {"total": len(results), "items": results, "search_time_ms": search_time_ms}
    except Exception as e:
        logger.error(f"文本搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )

@router.post("/vector")
async def vector_search(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """向量搜索 - 基于向量相似度的语义搜索 + Rerank精排"""
    try:
        logger.info(f"API请求: 向量搜索，查询: {search_request.query[:50]}..., 知识库ID: {search_request.knowledge_base_id}")
        
        service = SearchService(db)
        search_request.search_type = "vector"
        results = await service.vector_search(search_request)
        logger.info(f"API响应: 返回 {len(results)} 个搜索结果")
        return {"total": len(results), "items": results}
    except Exception as e:
        logger.error(f"向量搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向量搜索失败: {str(e)}"
        )

@router.post("/hybrid")
async def hybrid_search(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """混合搜索 - 结合关键词和语义的混合检索 + Rerank精排"""
    try:
        logger.info(f"API请求: 混合搜索，查询: {search_request.query[:50]}..., 知识库ID: {search_request.knowledge_base_id}")
        
        service = SearchService(db)
        search_request.search_type = "hybrid"
        results = await service.hybrid_search(search_request)
        logger.info(f"API响应: 返回 {len(results)} 个搜索结果")
        return {"total": len(results), "items": results}
    except Exception as e:
        logger.error(f"混合搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"混合搜索失败: {str(e)}"
        )

@router.get("/suggestions")
async def get_search_suggestions(
    query: str,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """搜索建议 - 提供搜索建议和自动补全"""
    try:
        logger.info(f"API请求: 搜索建议，查询: {query[:50]}..., 限制: {limit}")
        service = SearchService(db)
        request = SearchSuggestionRequest(query=query, limit=limit)
        results = await service.get_suggestions(request)
        logger.info(f"API响应: 返回 {len(results)} 个搜索建议")
        return results
    except Exception as e:
        logger.error(f"搜索建议API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取搜索建议失败: {str(e)}"
        )

@router.get("/history")
async def get_search_history(
    request: Request,
    limit: int = Query(
        settings.SEARCH_HISTORY_DEFAULT_LIMIT,
        ge=1,
        le=settings.SEARCH_HISTORY_MAX_LIMIT
    ),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取用户搜索历史"""
    try:
        user_id = get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
        
        logger.info(f"API请求: 获取搜索历史，用户ID: {user_id}, limit: {limit}, offset: {offset}")
        history_service = SearchHistoryService(db)
        results = await history_service.get_search_history(user_id=user_id, limit=limit, offset=offset)
        
        # 转换为响应格式
        history_list = []
        for h in results:
            history_list.append({
                "id": h.id,
                "query_text": h.query_text,
                "search_type": h.search_type,
                "knowledge_base_id": h.knowledge_base_id,
                "result_count": h.result_count,
                "search_time_ms": h.search_time_ms,
                "created_at": h.created_at.isoformat() if h.created_at else None
            })
        
        # 获取总数
        from app.models.search_history import SearchHistory
        total = db.query(SearchHistory).filter(
            SearchHistory.user_id == user_id,
            SearchHistory.is_deleted == False
        ).count()
        
        logger.info(f"API响应: 返回 {len(history_list)} 条搜索历史")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "list": history_list,
                "total": total
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取搜索历史API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取搜索历史失败: {str(e)}"
        )

@router.post("/save")
async def save_search(
    save_request: SaveSearchRequest,
    db: Session = Depends(get_db)
):
    """保存常用搜索"""
    try:
        logger.info(f"API请求: 保存搜索，查询: {save_request.query[:50]}..., 类型: {save_request.search_type}")
        service = SearchService(db)
        result = await service.save_search(save_request)
        logger.info(f"API响应: 搜索已保存")
        return result
    except Exception as e:
        logger.error(f"保存搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存搜索失败: {str(e)}"
        )

@router.delete("/history/{history_id}")
async def delete_search_history(
    history_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """删除搜索历史"""
    try:
        user_id = get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
        
        logger.info(f"API请求: 删除搜索历史，历史ID: {history_id}, 用户ID: {user_id}")
        history_service = SearchHistoryService(db)
        success = await history_service.delete_search_history(history_id, user_id=user_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="搜索历史不存在")
        
        logger.info(f"API响应: 搜索历史已删除")
        return {"code": 0, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除搜索历史API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除搜索历史失败: {str(e)}"
        )

@router.delete("/history")
async def clear_search_history(
    request: Request,
    db: Session = Depends(get_db)
):
    """清空搜索历史"""
    try:
        user_id = get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
        
        logger.info(f"API请求: 清空搜索历史，用户ID: {user_id}")
        history_service = SearchHistoryService(db)
        count = await history_service.clear_search_history(user_id)
        
        logger.info(f"API响应: 已清空 {count} 条搜索历史")
        return {"code": 0, "message": "清空成功", "data": {"deleted_count": count}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空搜索历史API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空搜索历史失败: {str(e)}"
        )

@router.post("/advanced")
async def advanced_search(
    advanced_request: SearchAdvancedRequest,
    db: Session = Depends(get_db)
):
    """高级搜索 - 支持复杂查询语法"""
    try:
        logger.info(f"API请求: 高级搜索，查询: {advanced_request.query[:50]}...")
        service = SearchService(db)
        results = await service.advanced_search(advanced_request)
        logger.info(f"API响应: 返回 {len(results)} 个搜索结果")
        return {"total": len(results), "items": results}
    except Exception as e:
        logger.error(f"高级搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"高级搜索失败: {str(e)}"
        )

@router.get("/facets", response_model=SearchFacetsResponse)
async def get_search_facets(
    query: str,
    knowledge_base_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取搜索分面信息 - 提供搜索结果的分面统计"""
    try:
        logger.info(f"API请求: 获取搜索分面，查询: {query[:50]}..., 知识库ID: {knowledge_base_id}")
        service = SearchService(db)
        results = await service.get_search_facets(query, knowledge_base_id)
        logger.info(f"API响应: 返回搜索分面信息")
        return results
    except Exception as e:
        logger.error(f"获取搜索分面API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取搜索分面失败: {str(e)}"
        )

@router.post("/similar", response_model=List[SearchResponse])
async def similar_search(
    similar_request: SimilarSearchRequest,
    db: Session = Depends(get_db)
):
    """相似搜索 - 基于文档相似度搜索"""
    try:
        logger.info(f"API请求: 相似搜索，文档ID: {similar_request.document_id}, 分块ID: {similar_request.chunk_id}")
        service = SearchService(db)
        results = await service.similar_search(similar_request)
        logger.info(f"API响应: 返回 {len(results)} 个相似搜索结果")
        return results
    except Exception as e:
        logger.error(f"相似搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"相似搜索失败: {str(e)}"
        )
