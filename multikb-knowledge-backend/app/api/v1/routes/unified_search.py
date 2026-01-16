"""
Unified Search API
统一搜索 API - 文档+代码混合搜索
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.logging import logger
from app.core.response import success_response, error_response
from app.dependencies.database import get_db
from app.services.unified_search_service import get_unified_search_service


router = APIRouter(prefix="/unified-search", tags=["统一搜索"])


# ============================================
# 请求模型
# ============================================

class UnifiedSearchRequest(BaseModel):
    """统一搜索请求"""
    query: str
    knowledge_base_id: Optional[int] = None
    search_scope: List[str] = ["documents", "code"]
    search_mode: str = "hybrid"  # hybrid/vector/keyword
    top_k: int = 20
    filters: Optional[dict] = None


# ============================================
# API 端点
# ============================================

@router.post("")
async def unified_search(
    request: UnifiedSearchRequest,
    db: Session = Depends(get_db)
):
    """
    统一搜索（文档 + 代码）
    
    Args:
        request: 搜索请求
        
    Returns:
        搜索结果（混合并排序）
    """
    try:
        search_service = get_unified_search_service(db)
        
        results = await search_service.search(
            query=request.query,
            knowledge_base_id=request.knowledge_base_id,
            search_scope=request.search_scope,
            search_mode=request.search_mode,
            top_k=request.top_k,
            filters=request.filters
        )
        
        return success_response(results)
    
    except Exception as e:
        logger.error(f"统一搜索失败: {e}")
        return error_response(f"统一搜索失败: {str(e)}")


@router.get("/knowledge-bases/{kb_id}")
async def search_in_knowledge_base(
    kb_id: int,
    query: str,
    search_scope: str = "all",  # all/documents/code
    search_mode: str = "hybrid",
    top_k: int = 20,
    db: Session = Depends(get_db)
):
    """
    在指定知识库中搜索
    
    Args:
        kb_id: 知识库ID
        query: 搜索查询
        search_scope: 搜索范围
        search_mode: 搜索模式
        top_k: 返回数量
        
    Returns:
        搜索结果
    """
    try:
        # 转换搜索范围
        scope_map = {
            "all": ["documents", "code"],
            "documents": ["documents"],
            "code": ["code"]
        }
        search_scope_list = scope_map.get(search_scope, ["documents", "code"])
        
        search_service = get_unified_search_service(db)
        
        results = await search_service.search(
            query=query,
            knowledge_base_id=kb_id,
            search_scope=search_scope_list,
            search_mode=search_mode,
            top_k=top_k
        )
        
        return success_response(results)
    
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return error_response(f"知识库搜索失败: {str(e)}")


@router.get("/code/files")
async def search_code_files(
    query: str,
    repository_id: Optional[int] = None,
    language: Optional[str] = None,
    directory: Optional[str] = None,  # 新增：按目录路径前缀过滤
    top_k: int = 20,
    db: Session = Depends(get_db)
):
    """
    搜索代码文件
    
    Args:
        query: 搜索查询
        repository_id: 仓库ID筛选
        language: 语言筛选
        directory: 目录路径前缀（如 "src/utils/"），只返回该目录下的文件
        top_k: 返回数量
        
    Returns:
        代码文件列表
    """
    try:
        filters = {}
        if repository_id:
            filters['repository_id'] = repository_id
        if language:
            filters['language'] = language
        if directory:
            filters['directory'] = directory  # 支持按目录过滤
        
        search_service = get_unified_search_service(db)
        
        results = await search_service.search(
            query=query,
            search_scope=["code"],
            search_mode="hybrid",
            top_k=top_k,
            filters=filters
        )
        
        # 只返回代码文件类型的结果
        code_files = [r for r in results['results'] if r['type'] == 'code_file']
        
        return success_response({
            "total": len(code_files),
            "results": code_files
        })
    
    except Exception as e:
        logger.error(f"搜索代码文件失败: {e}")
        return error_response(f"搜索代码文件失败: {str(e)}")


@router.get("/code/symbols")
async def search_code_symbols(
    query: str,
    repository_id: Optional[int] = None,
    symbol_type: Optional[str] = None,
    top_k: int = 20,
    db: Session = Depends(get_db)
):
    """
    搜索代码符号
    
    Args:
        query: 搜索查询
        repository_id: 仓库ID筛选
        symbol_type: 符号类型筛选
        top_k: 返回数量
        
    Returns:
        代码符号列表
    """
    try:
        filters = {}
        if repository_id:
            filters['repository_id'] = repository_id
        if symbol_type:
            filters['symbol_type'] = symbol_type
        
        search_service = get_unified_search_service(db)
        
        results = await search_service.search(
            query=query,
            search_scope=["code"],
            search_mode="hybrid",
            top_k=top_k,
            filters=filters
        )
        
        # 只返回代码符号类型的结果
        code_symbols = [r for r in results['results'] if r['type'] == 'code_symbol']
        
        return success_response({
            "total": len(code_symbols),
            "results": code_symbols
        })
    
    except Exception as e:
        logger.error(f"搜索代码符号失败: {e}")
        return error_response(f"搜索代码符号失败: {str(e)}")
