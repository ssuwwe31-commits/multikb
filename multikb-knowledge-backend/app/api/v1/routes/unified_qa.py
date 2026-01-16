"""
Unified QA API
统一问答 API - 支持文档+代码的上下文问答
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.logging import logger
from app.core.response import success_response, error_response
from app.dependencies.database import get_db
from app.services.unified_qa_service import get_unified_qa_service


router = APIRouter(prefix="/unified-qa", tags=["统一问答"])


# ============================================
# 请求模型
# ============================================

class UnifiedQARequest(BaseModel):
    """统一问答请求"""
    question: str
    knowledge_base_id: Optional[int] = None
    search_scope: List[str] = ["documents", "code"]
    max_context_items: int = 5
    include_code_context: bool = True


class CodeExamplesRequest(BaseModel):
    """代码示例请求"""
    concept: str
    knowledge_base_id: Optional[int] = None
    language: Optional[str] = None
    limit: int = 5


# ============================================
# API 端点
# ============================================

@router.post("")
async def unified_qa(
    request: UnifiedQARequest,
    db: Session = Depends(get_db)
):
    """
    统一问答（文档 + 代码）
    
    Args:
        request: 问答请求
        
    Returns:
        答案 + 来源
    """
    try:
        qa_service = get_unified_qa_service(db)
        
        result = await qa_service.answer_question(
            question=request.question,
            knowledge_base_id=request.knowledge_base_id,
            search_scope=request.search_scope,
            max_context_items=request.max_context_items,
            include_code_context=request.include_code_context
        )
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"统一问答失败: {e}")
        return error_response(f"统一问答失败: {str(e)}")


@router.post("/knowledge-bases/{kb_id}/ask")
async def ask_knowledge_base(
    kb_id: int,
    question: str,
    include_code: bool = True,
    max_sources: int = 5,
    db: Session = Depends(get_db)
):
    """
    向知识库提问（包含代码上下文）
    
    Args:
        kb_id: 知识库ID
        question: 用户问题
        include_code: 是否包含代码上下文
        max_sources: 最大来源数量
        
    Returns:
        答案 + 来源
    """
    try:
        qa_service = get_unified_qa_service(db)
        
        search_scope = ["documents", "code"] if include_code else ["documents"]
        
        result = await qa_service.answer_question(
            question=question,
            knowledge_base_id=kb_id,
            search_scope=search_scope,
            max_context_items=max_sources,
            include_code_context=include_code
        )
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"知识库问答失败: {e}")
        return error_response(f"知识库问答失败: {str(e)}")


@router.post("/code-examples")
async def get_code_examples(
    request: CodeExamplesRequest,
    db: Session = Depends(get_db)
):
    """
    获取代码示例（根据概念/关键词）
    
    Args:
        request: 代码示例请求
        
    Returns:
        代码示例列表
    """
    try:
        qa_service = get_unified_qa_service(db)
        
        examples = await qa_service.get_code_examples(
            concept=request.concept,
            knowledge_base_id=request.knowledge_base_id,
            language=request.language,
            limit=request.limit
        )
        
        return success_response({
            "concept": request.concept,
            "total": len(examples),
            "examples": examples
        })
    
    except Exception as e:
        logger.error(f"获取代码示例失败: {e}")
        return error_response(f"获取代码示例失败: {str(e)}")


@router.get("/repositories/{repo_id}/explain")
async def explain_repository(
    repo_id: int,
    question: str = "这个代码仓库的主要功能是什么？",
    db: Session = Depends(get_db)
):
    """
    解释代码仓库（基于整体分析）
    
    Args:
        repo_id: 仓库ID
        question: 问题（可自定义）
        
    Returns:
        仓库解释
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 获取仓库信息
        repo = db.query(CodeRepository).filter(
            CodeRepository.id == repo_id
        ).first()
        
        if not repo:
            return error_response("仓库不存在")
        
        qa_service = get_unified_qa_service(db)
        
        # 问答（限定在该仓库的代码）
        result = await qa_service.answer_question(
            question=question,
            knowledge_base_id=repo.knowledge_base_id,
            search_scope=["code"],
            max_context_items=10,
            include_code_context=True
        )
        
        return success_response({
            "repository_id": repo_id,
            "repository_name": repo.repo_name,
            "question": question,
            "answer": result['answer'],
            "sources": result['sources']
        })
    
    except Exception as e:
        logger.error(f"解释代码仓库失败: {e}")
        return error_response(f"解释代码仓库失败: {str(e)}")
