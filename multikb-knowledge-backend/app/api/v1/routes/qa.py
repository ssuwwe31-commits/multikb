"""
QA API Routes
根据知识问答系统设计文档实现
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Request
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import json
import httpx
import re

from app.schemas.qa import (
    QASessionCreate, QASessionResponse, QASessionListResponse,
    QAMultimodalQuestionRequest, QAMultimodalQuestionResponse,
    QAImageSearchRequest, QAImageSearchResponse,
    QAHistoryResponse, QAHistorySearchRequest, QAHistorySearchResponse,
    QAModelResponse, QASessionConfigUpdate, KnowledgeBaseListResponse,
    QAExternalSearchRequest, QAExternalSearchResponse
)
from app.services.qa_service import QAService
from app.services.multimodal_processing_service import MultimodalProcessingService
from app.services.fallback_strategy_service import FallbackStrategyService
from app.services.qa_history_service import QAHistoryService
from app.services.external_search_service import ExternalSearchService, ExternalSearchRateLimitError
from app.services.ollama_service import OllamaService
from app.services.opensearch_service import OpenSearchService
from app.models.qa_external_search import QAExternalSearchRecord
from app.dependencies.database import get_db
from app.core.logging import logger
from app.config.settings import settings

router = APIRouter()
external_search_service = ExternalSearchService()


def get_current_user_id(request: Request) -> int:
    """从请求中获取当前用户ID"""
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户信息")
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户ID")

# 1. 知识库选择功能

@router.get("/knowledge-bases", response_model=KnowledgeBaseListResponse)
async def get_knowledge_bases(
    request: Request,
    category_id: Optional[int] = None,
    status: str = "active",
    page: int = 1,
    size: int = settings.QA_DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db)
):
    """获取知识库列表 - 只返回当前用户有权限的知识库"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取知识库列表，分类ID: {category_id}, 状态: {status}, 用户ID: {user_id}")
        
        # 使用 KnowledgeBaseService 来获取用户有权限的知识库列表
        from app.services.knowledge_base_service import KnowledgeBaseService
        kb_service = KnowledgeBaseService(db)
        items, total = await kb_service.get_knowledge_bases_paginated(
            page=page,
            size=size,
            user_id=user_id
        )
        
        # 转换为 QA 模块期望的格式
        knowledge_bases = []
        for kb in items:
            knowledge_bases.append({
                "id": kb.get("id"),
                "name": kb.get("name"),
                "description": kb.get("description", ""),
                "category_id": kb.get("category_id"),
                "category_name": kb.get("category_name", ""),
                "document_count": kb.get("document_count", 0),
                "storage_size": kb.get("storage_size", 0),
                "tags": kb.get("tags", []),
                "status": "active" if kb.get("is_active", True) else "inactive",
                "created_at": kb.get("created_at")
            })
        
        logger.info(f"API响应: 返回 {len(knowledge_bases)} 个知识库")
        
        from app.schemas.qa import KnowledgeBaseListResponse
        return KnowledgeBaseListResponse(
            knowledge_bases=knowledge_bases,
            pagination={
                "page": page,
                "size": size,
                "total": total,
                "total_pages": (total + size - 1) // size if size > 0 else 0
            }
        )
        
    except Exception as e:
        logger.error(f"获取知识库列表API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表失败: {str(e)}"
        )

@router.get("/knowledge-bases/{kb_id}", response_model=QASessionResponse)
def get_knowledge_base_detail(
    request: Request,
    kb_id: int,
    db: Session = Depends(get_db)
):
    """获取知识库详情 - 根据设计文档实现，需要 kb:view 权限"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取知识库详情 {kb_id}, 用户ID: {user_id}")
        
        # 权限检查：确保用户有查看权限
        from app.services.permission_service import KnowledgeBasePermissionService
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(kb_id, user_id, "kb:view")
        
        service = QAService(db)
        result = service.get_knowledge_base_detail(kb_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在或无权访问"
            )
        
        logger.info(f"API响应: 成功获取知识库详情 {result.name}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库详情API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库详情失败: {str(e)}"
        )

@router.get("/search-types")
def get_search_types():
    """获取查询方式配置 - 根据设计文档实现"""
    try:
        logger.info("API请求: 获取查询方式配置")
        
        search_types = [
            {
                "type": "vector",
                "name": "向量检索",
                "description": "基于语义相似度的向量搜索",
                "icon": "vector-search",
                "recommended": True
            },
            {
                "type": "keyword",
                "name": "关键词检索", 
                "description": "基于BM25算法的关键词搜索",
                "icon": "keyword-search",
                "recommended": False
            },
            {
                "type": "hybrid",
                "name": "混合检索",
                "description": "向量检索和关键词检索的加权融合",
                "icon": "hybrid-search",
                "recommended": True
            },
            {
                "type": "exact",
                "name": "精确匹配",
                "description": "精确的文本匹配搜索",
                "icon": "exact-search",
                "recommended": False
            },
            {
                "type": "fuzzy",
                "name": "模糊搜索",
                "description": "支持通配符和正则表达式的搜索",
                "icon": "fuzzy-search",
                "recommended": False
            },
            {
                "type": "image",
                "name": "图片搜索",
                "description": "以图找图和以文找图搜索",
                "icon": "image-search",
                "recommended": True
            }
        ]
        
        logger.info("API响应: 成功获取查询方式配置")
        return {"search_types": search_types}
        
    except Exception as e:
        logger.error(f"获取查询方式配置API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取查询方式配置失败: {str(e)}"
        )

# 2. 会话管理功能

@router.post("/sessions", response_model=QASessionResponse)
def create_qa_session(
    session_data: QASessionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """创建问答会话 - 根据设计文档实现"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 创建问答会话，知识库ID: {session_data.knowledge_base_id}, 用户ID: {user_id}")
        
        service = QAService(db)
        result = service.create_qa_session(session_data, user_id=user_id)

        # 兼容服务层返回 Pydantic 模型或 dict
        try:
            sid = getattr(result, 'session_id', None) or (result.get('session_id') if isinstance(result, dict) else None)
        except Exception:
            sid = None
        logger.info(f"API响应: 成功创建会话 {sid if sid else '[unknown]'}")
        return result
        
    except Exception as e:
        logger.error(f"创建问答会话API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建问答会话失败: {str(e)}"
        )

@router.get("/sessions", response_model=QASessionListResponse)
def get_qa_sessions(
    request: Request,
    page: int = 1,
    size: int = settings.QA_DEFAULT_PAGE_SIZE,
    knowledge_base_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取会话列表 - 根据设计文档实现，只返回当前用户的会话"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取会话列表，页码: {page}, 大小: {size}, 用户ID: {user_id}")
        
        service = QAService(db)
        result = service.get_qa_sessions(
            page=page,
            size=size,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id  # 添加用户ID过滤
        )
        
        logger.info(f"API响应: 返回 {len(result.sessions)} 个会话")
        return result
        
    except Exception as e:
        logger.error(f"获取会话列表API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=QASessionResponse)
async def get_qa_session_detail(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db)
):
    """获取会话详情 - 根据设计文档实现，从OpenSearch加载完整内容，只返回当前用户的会话"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取会话详情 {session_id}, 用户ID: {user_id}")
        
        service = QAService(db)
        result = await service.get_qa_session_detail(session_id, user_id=user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权访问"
            )
        
        # 兼容 dict / 模型
        try:
            sname = getattr(result, 'session_name', None) or (result.get('session_name') if isinstance(result, dict) else None)
        except Exception:
            sname = None
        logger.info(f"API响应: 成功获取会话详情 {sname if sname else '[unknown]'}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话详情失败: {str(e)}"
        )

@router.delete("/sessions/{session_id}")
async def delete_qa_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """删除会话 - 硬删除：删除数据库和OpenSearch中的所有相关数据"""
    try:
        logger.info(f"API请求: 硬删除会话 {session_id}")
        
        service = QAService(db)
        success = await service.delete_qa_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        logger.info(f"API响应: 成功硬删除会话 {session_id}")
        return {"message": "会话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除会话失败: {str(e)}"
        )

# 3. 多模态问答功能

@router.post("/sessions/{session_id}/multimodal-questions", response_model=QAMultimodalQuestionResponse)
async def ask_multimodal_question(
    session_id: str,
    text_content: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    input_type: str = Form("text"),
    include_history: bool = Form(True),
    max_history: int = Form(settings.QA_DEFAULT_MAX_HISTORY),
    similarity_threshold: float = Form(settings.SEARCH_VECTOR_THRESHOLD),
    max_sources: int = Form(settings.QA_DEFAULT_MAX_SOURCES),
    search_type: str = Form("hybrid"),
    db: Session = Depends(get_db)
):
    """多模态问答接口 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 多模态问答，会话ID: {session_id}, 输入类型: {input_type}")
        
        # 验证输入类型
        if input_type not in ["text", "image", "multimodal"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="输入类型必须是 text、image 或 multimodal"
            )
        
        # 验证输入内容
        if input_type == "text" and not text_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文本输入类型需要提供文本内容"
            )
        
        if input_type == "image" and not image_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图片输入类型需要提供图片文件"
            )
        
        if input_type == "multimodal" and (not text_content or not image_file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图文混合输入类型需要同时提供文本内容和图片文件"
            )
        
        # 多模态处理服务
        multimodal_service = MultimodalProcessingService(db)
        
        # 处理多模态输入
        processed_input = await multimodal_service.process_multimodal_input(
            text_content=text_content,
            image_file=image_file,
            input_type=input_type
        )
        logger.debug(
            "[QA][API] processed_input summary: session=%s text_len=%s image=%s steps=%s",
            session_id,
            len((processed_input.get("text_data") or {}).get("cleaned_text", "")) if processed_input else 0,
            "yes" if processed_input.get("image_data") else "no",
            (processed_input or {}).get("processing_steps")
        )
        
        # 问答服务
        qa_service = QAService(db)
        
        # 执行问答
        result = await qa_service.ask_multimodal_question(
            session_id=session_id,
            processed_input=processed_input,
            include_history=include_history,
            max_history=max_history,
            similarity_threshold=similarity_threshold,
            max_sources=max_sources,
            search_type=search_type
        )
        
        logger.info(f"API响应: 多模态问答完成，问题ID: {result.question_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"多模态问答API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"多模态问答失败: {str(e)}"
        )

# 4. 图片搜索功能

@router.post("/sessions/{session_id}/image-search", response_model=QAImageSearchResponse)
async def search_images(
    session_id: str,
    image_file: UploadFile = File(...),
    search_type: str = "image-to-image",
    similarity_threshold: float = settings.SEARCH_VECTOR_THRESHOLD,
    max_results: int = settings.QA_DEFAULT_MAX_RESULTS,
    knowledge_base_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """图片搜索接口 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 图片搜索，会话ID: {session_id}, 搜索类型: {search_type}")
        
        # 验证搜索类型
        if search_type not in ["image-to-image", "text-to-image"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="搜索类型必须是 image-to-image 或 text-to-image"
            )
        
        # 多模态处理服务
        multimodal_service = MultimodalProcessingService(db)
        
        # 处理图片输入
        processed_image = await multimodal_service.process_image_input(image_file)
        
        # 图片搜索服务
        qa_service = QAService(db)
        
        # 执行图片搜索
        result = await qa_service.search_images(
            session_id=session_id,
            processed_image=processed_image,
            search_type=search_type,
            similarity_threshold=similarity_threshold,
            max_results=max_results,
            knowledge_base_id=knowledge_base_id
        )
        
        logger.info(f"API响应: 图片搜索完成，找到 {len(result.results)} 个结果")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图片搜索失败: {str(e)}"
        )


@router.post("/external-search", response_model=QAExternalSearchResponse)
async def qa_external_search(
    payload: QAExternalSearchRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """触发 SearxNG 联网搜索兜底"""
    if not settings.SEARXNG_URL or not settings.EXTERNAL_SEARCH_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="外部搜索未启用")

    try:
        user_id = get_current_user_id(request)
    except HTTPException:
        user_id = None

    intent = await _classify_external_intent(payload.question)
    logger.info("[外部搜索] 问题意图识别结果 intent=%s question=%s", intent, payload.question[:80])
    metadata = {
        "knowledge_base_hits": payload.knowledge_base_hits,
        "top_score": payload.top_score,
        "answer_confidence": payload.answer_confidence,
        "context_preview": (payload.context or "")[:500] if payload.context else None,
        "detected_intent": intent,
    }

    summary_text: Optional[str] = None
    record: Optional[QAExternalSearchRecord] = None

    try:
        result = await external_search_service.search(
            question=payload.question,
            context=payload.context,
            user_id=user_id,
            limit=payload.limit,
            metadata=metadata,
            intent=intent,
        )
        logger.info(
            "[外部搜索] SearxNG 查询完成 intent=%s from_cache=%s latency=%s result_count=%s",
            intent,
            result.get("from_cache"),
            result.get("latency"),
            len(result.get("results", []) or []),
        )
        if settings.EXTERNAL_SEARCH_SUMMARY_ENABLED:
            summary_text = await _summarize_external_results(
                question=payload.question,
                results=result.get("results", []),
                db=db,
            )

        # 写入 MySQL
        try:
            record = QAExternalSearchRecord(
                question=payload.question.strip(),
                search_query=result.get("query"),
                session_id=payload.conversation_id,
                user_id=str(user_id) if user_id is not None else None,
                summary=summary_text,
                results=result.get("results", []),
                trigger_metadata=metadata,
                from_cache=bool(result.get("from_cache")),
                latency=result.get("latency"),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        except Exception as db_exc:
            db.rollback()
            logger.warning(f"外部搜索记录入库失败: {db_exc}")
            record = None

        # 写入 OpenSearch
        if record:
            document = {
                "record_id": record.id,
                "question": record.question,
                "search_query": record.search_query,
                "summary": summary_text,
                "session_id": record.session_id,
                "user_id": record.user_id,
                "results": result.get("results", []),
                "metadata": metadata,
                "from_cache": bool(result.get("from_cache")),
                "latency": result.get("latency"),
                "created_at": (record.created_at or datetime.utcnow()).isoformat(),
            }
            try:
                os_service = OpenSearchService()
                await os_service.index_document(
                    os_service.external_search_index,
                    f"external_search_{record.id}",
                    document,
                )
            except Exception as os_exc:
                logger.warning(f"外部搜索记录索引失败: {os_exc}")

        return QAExternalSearchResponse(
            triggered=True,
            from_cache=result.get("from_cache", False),
            query=result.get("query"),
            latency=result.get("latency"),
            results=result.get("results", []),
            summary=summary_text,
        )
    except ExternalSearchRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.error(f"调用 SearxNG 失败: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="外部搜索服务异常") from exc
    except Exception as exc:
        logger.error(f"外部搜索API错误: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="外部搜索失败") from exc


async def _summarize_external_results(
    question: str,
    results: List[Dict[str, Any]],
    db: Session,
) -> Optional[str]:
    """调用 LLM 对外部搜索结果生成摘要"""
    if (
        not results
        or not settings.EXTERNAL_SEARCH_SUMMARY_ENABLED
    ):
        return None

    model_name = (
        settings.EXTERNAL_SEARCH_SUMMARY_MODEL
        or settings.QA_SUMMARY_MODEL
        or settings.OLLAMA_MODEL
    )
    if not model_name:
        return None

    limited = results[: max(1, settings.EXTERNAL_SEARCH_SUMMARY_MAX_ITEMS)]
    lines: List[str] = []
    for idx, item in enumerate(limited, 1):
        title = (item.get("title") or "").strip() or "未命名"
        source = (item.get("source") or item.get("url") or "").strip()
        snippet = (item.get("snippet") or "").strip()
        if len(snippet) > 220:
            snippet = snippet[:220] + "..."
        lines.append(
            f"{idx}. 标题: {title}\n   来源: {source}\n   摘要: {snippet or '暂无摘要'}"
        )
    context = "\n".join(lines)
    prompt = (
        "你是一名企业内部的知识助手，请根据以下外部搜索结果，"
        "针对用户的问题总结 3-4 条中文要点。确保内容准确，不要杜撰。"
        "如果信息不足以回答，请说明“外部信息不足”。"
        f"\n用户问题：{question}\n外部搜索结果：\n{context}\n请开始总结："
    )

    ollama = OllamaService(db)
    try:
        summary = await ollama.generate_text(prompt, model=model_name)
        cleaned = _clean_summary_text(summary)
        logger.info(
            "[外部搜索] 摘要生成完成 model=%s has_summary=%s", model_name, bool(cleaned)
        )
        return cleaned
    except Exception as exc:
        logger.warning(f"外部搜索摘要生成失败: {exc}")
        return None


async def _classify_external_intent(question: str) -> str:
    """调用 LLM 识别外部搜索的意图类别"""
    model_name = (
        settings.EXTERNAL_SEARCH_INTENT_MODEL
        or settings.QA_SUMMARY_MODEL
        or settings.OLLAMA_MODEL
    )
    if not model_name:
        return "general"

    prompt = (
        "你是一个分类器，请判断用户问题更接近哪一类搜索意图。"
        "候选类别只有：news（新闻、热点、头条）、tech（技术教程/故障排查）、general（无法判断或其他）。"
        "输出格式为 JSON，如 {\"intent\": \"news\"}，不要添加其它内容。\n"
        f"用户问题：{question}"
    )
    ollama = OllamaService(None)
    try:
        response = await ollama.generate_text(prompt, model=model_name)
        intent = _extract_intent_from_response(response)
        logger.debug("[外部搜索] 意图识别响应: %s -> %s", response, intent)
        return intent
    except Exception as exc:
        logger.warning(f"外部搜索意图识别失败: {exc}")
        return "general"


def _extract_intent_from_response(response: str) -> str:
    """从模型输出解析 intent，容错处理非 JSON 场景"""
    import json
    clean = (response or "").strip()
    if not clean:
        return "general"
    try:
        # 尝试找到第一个 JSON 片段
        if not clean.startswith("{"):
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1 and end > start:
                clean = clean[start : end + 1]
        data = json.loads(clean)
        intent = (data.get("intent") or "general").lower()
        if intent not in {"news", "tech", "general"}:
            intent = "general"
        return intent
    except Exception:
        lower_resp = clean.lower()
        if any(k in lower_resp for k in ["news", "headline", "热点", "新闻"]):
            return "news"
        if any(k in lower_resp for k in ["tech", "技术", "教程", "故障"]):
            return "tech"
        return "general"


def _clean_summary_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cleaned = re.sub(r"</?think>", "", text, flags=re.IGNORECASE)
    return cleaned.strip() or None

# 5. 流式问答功能

@router.websocket("/sessions/{session_id}/stream")
async def websocket_stream(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """流式问答WebSocket接口 - 根据设计文档实现"""
    await websocket.accept()
    
    try:
        logger.info(f"WebSocket连接: 流式问答，会话ID: {session_id}")
        
        qa_service = QAService(db)
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            if data.get("type") == "question":
                # 处理问答请求
                question_data = data.get("data", {})
                
                # 执行流式问答
                async for chunk in qa_service.stream_answer(
                    session_id=session_id,
                    question_data=question_data
                ):
                    await websocket.send_json({
                        "type": "content_chunk",
                        "data": chunk
                    })
                
                # 发送完成通知
                await websocket.send_json({
                    "type": "completion",
                    "data": {"status": "completed"}
                })
            
            elif data.get("type") == "close":
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: 会话ID {session_id}")
    except Exception as e:
        logger.error(f"WebSocket流式问答错误: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "data": {"message": str(e)}
        })

# 6. 配置管理功能

@router.get("/models", response_model=List[QAModelResponse])
def get_available_models():
    """获取可用模型 - 根据设计文档实现"""
    try:
        logger.info("API请求: 获取可用模型")
        
        models = {
            "llm_models": [
                {
                    "name": "llama2",
                    "display_name": "Llama 2",
                    "description": "Meta的Llama 2大语言模型",
                    "language": "multilingual",
                    "size": "7B",
                    "status": "available"
                },
                {
                    "name": "codellama",
                    "display_name": "Code Llama",
                    "description": "专门用于代码生成的Llama模型",
                    "language": "multilingual",
                    "size": "7B",
                    "status": "available"
                }
            ],
            "embedding_models": [
                {
                    "name": "nomic-embed-text",
                    "display_name": "Nomic Embed Text",
                    "description": "Nomic的文本嵌入模型",
                    "dimension": settings.TEXT_EMBEDDING_DIMENSION,
                    "language": "multilingual",
                    "status": "available"
                },
                {
                    "name": "mxbai-embed-large",
                    "display_name": "MXBai Embed Large",
                    "description": "MXBai的大规模嵌入模型",
                    "dimension": settings.IMAGE_EMBEDDING_DIMENSION,
                    "language": "multilingual",
                    "status": "available"
                }
            ]
        }
        
        logger.info("API响应: 成功获取可用模型")
        return models
        
    except Exception as e:
        logger.error(f"获取可用模型API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用模型失败: {str(e)}"
        )

@router.put("/sessions/{session_id}/config")
def update_session_config(
    session_id: str,
    config_update: QASessionConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新会话配置 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 更新会话配置 {session_id}")
        
        service = QAService(db)
        result = service.update_session_config(session_id, config_update)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        logger.info(f"API响应: 成功更新会话配置 {session_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会话配置API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新会话配置失败: {str(e)}"
        )

# 7. 历史记录查询功能

@router.post("/history/search", response_model=QAHistorySearchResponse)
def search_qa_history(
    search_request: QAHistorySearchRequest,
    db: Session = Depends(get_db)
):
    """搜索历史问答 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 搜索历史问答，关键词: {search_request.search_keyword}")
        
        history_service = QAHistoryService(db)
        result = history_service.search_qa_history(search_request)
        
        logger.info(f"API响应: 找到 {len(result.search_results)} 个搜索结果")
        return result
        
    except Exception as e:
        logger.error(f"搜索历史问答API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索历史问答失败: {str(e)}"
        )

@router.get("/history/{question_id}", response_model=Dict[str, Any])
def get_qa_detail(
    question_id: str,
    db: Session = Depends(get_db)
):
    """获取问答详情 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取问答详情 {question_id}")
        
        history_service = QAHistoryService(db)
        result = history_service.get_qa_detail(question_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答记录不存在"
            )
        
        logger.info(f"API响应: 成功获取问答详情 {question_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取问答详情API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取问答详情失败: {str(e)}"
        )

@router.get("/history", response_model=List[QAHistoryResponse])
async def get_qa_history(
    request: Request,
    skip: int = 0,
    limit: int = settings.QA_MAX_PAGE_SIZE,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取问答历史 - 只返回当前用户的历史记录"""
    # 获取当前用户ID
    user_id = get_current_user_id(request)
    service = QAService(db)
    # 通过 session_id 间接过滤：先检查 session 是否属于当前用户
    if session_id:
        from app.models.qa_session import QASession
        session = db.query(QASession).filter(
            QASession.session_id == session_id,
            QASession.user_id == user_id
        ).first()
        if not session:
            return []  # 如果会话不属于当前用户，返回空列表
    
    # 直接调用 history_service，传入用户ID字符串
    from app.services.qa_history_service import QAHistoryService
    history_service = QAHistoryService(db)
    page = (skip // limit) + 1 if limit > 0 else 1
    result = await history_service.get_qa_history(
        user_id=str(user_id),  # history_service 期望字符串类型
        page=page,
        size=limit
    )
    # 转换返回格式
    return result.get("items", [])
