"""
Search Service: 向量 + 关键词 融合检索 + Rerank精排
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text as sql_text
from app.services.opensearch_service import OpenSearchService
from app.services.vector_service import VectorService
from app.services.rerank_service import RerankService
from app.services.document_service import DocumentService
from app.schemas.search import SearchRequest, SearchResponse
from sqlalchemy.orm import Session
from app.core.logging import logger
from app.config.settings import settings


class SearchService:
    """搜索服务 - 支持向量搜索、关键词搜索、混合搜索和Rerank精排"""
    
    def __init__(self, db: Session):
        self.db = db
        self.os = OpenSearchService()
        self.vs = VectorService(db)
        self.rerank_service = RerankService()

    def _json_load(self, v):
        try:
            import json
            return json.loads(v) if isinstance(v, str) else v
        except Exception:
            return None

    def _load_table_by_group_uid(self, table_group_uid: str) -> Dict[str, Any]:
        try:
            rows = self.db.execute(sql_text(
                "SELECT table_uid, document_id, element_index, n_rows, n_cols, headers_json, cells_json, spans_json, stats_json, part_index, part_count, row_range "
                "FROM document_tables WHERE table_group_uid=:uid ORDER BY part_index ASC"
            ), {"uid": table_group_uid}).fetchall()
            if not rows:
                return {}
            headers = None
            cells: List[List[str]] = []
            for r in rows:
                (table_uid, doc_id, element_index, n_rows, n_cols, headers_json, cells_json, spans_json, stats_json, part_index, part_count, row_range) = r
                if headers is None:
                    headers = self._json_load(headers_json) or {}
                part_cells = self._json_load(cells_json) or []
                if isinstance(part_cells, list):
                    cells.extend([[str(c) if c is not None else "" for c in row] if isinstance(row, list) else [str(row)] for row in part_cells])
            return {"headers": headers, "cells": cells}
        except Exception:
            return {}

    def _load_table_by_uid(self, table_uid: str) -> Dict[str, Any]:
        try:
            r = self.db.execute(sql_text(
                "SELECT headers_json, cells_json FROM document_tables WHERE table_uid=:uid"
            ), {"uid": table_uid}).fetchone()
            if not r:
                return {}
            headers_json, cells_json = r
            headers = self._json_load(headers_json) or {}
            cells = self._json_load(cells_json) or []
            if isinstance(cells, list):
                cells = [[str(c) if c is not None else "" for c in row] if isinstance(row, list) else [str(row)] for row in cells]
            else:
                cells = []
            return {"headers": headers, "cells": cells}
        except Exception:
            return {}

    def _hydrate_table_by_chunk(self, document_id: int, chunk_id: int) -> Dict[str, Any]:
        """兜底：从 chunks 表读取 meta，再按编辑页逻辑补齐表格 cells"""
        try:
            from app.models.chunk import DocumentChunk
            chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id,
                DocumentChunk.document_id == document_id
            ).first()
            if not chunk:
                return {}
            meta = self._json_load(getattr(chunk, 'meta', None)) or {}
            group_uid = meta.get('table_group_uid')
            table_uid = meta.get('table_id') or meta.get('table_uid')
            if group_uid:
                return self._load_table_by_group_uid(group_uid)
            if table_uid:
                return self._load_table_by_uid(table_uid)
            # 旧数据直接带 table_data
            table_data = (meta or {}).get('table_data') or {}
            cells = table_data.get('cells')
            if isinstance(cells, list) and cells:
                return {"headers": None, "cells": cells}
            return {}
        except Exception:
            return {}
    
    async def mixed_search(
        self,
        query_text: str,
        knowledge_base_id: Optional[List[int]] = None,
        top_k: Optional[int] = None,
        alpha: float = None,
        use_keywords: bool = True,
        use_vector: bool = True,
        similarity_threshold: Optional[float] = None,  # 改为 None，使用配置值
        category_id: Optional[int] = None,
        min_rerank_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """向量 + 关键词 融合检索 + Rerank精排
        
        Args:
            query_text: 查询文本
            knowledge_base_id: 知识库ID（可选）
            top_k: 返回结果数量（如果为None，使用配置的RERANK_TOP_K）
            alpha: 向量搜索权重（0.0-1.0），关键词搜索权重为(1-alpha)
            use_keywords: 是否使用关键词搜索
            use_vector: 是否使用向量搜索
            similarity_threshold: 相似度阈值（如果为None，使用配置的SEARCH_VECTOR_THRESHOLD）
            
        Returns:
            搜索结果列表（经过rerank精排，返回top_k个结果）
        """
        results: List[Dict[str, Any]] = []
        vector_hits: List[Dict[str, Any]] = []
        keyword_hits: List[Dict[str, Any]] = []
        
        # 确定返回数量（优先使用配置的RERANK_TOP_K）
        if top_k is None:
            top_k = settings.SEARCH_VECTOR_TOPK or settings.RERANK_TOP_K
        
        # 确定相似度阈值（优先使用传入参数，否则使用配置值）
        if similarity_threshold is None:
            similarity_threshold = settings.SEARCH_VECTOR_THRESHOLD
        
        # 为了rerank，需要召回更多候选（通常取top_k的2-3倍）
        recall_limit = top_k * 3  # 召回更多候选，供rerank精排
        
        try:
            if use_vector:
                logger.info(f"开始向量搜索: {query_text[:50]}...")
                qv = self.vs.generate_embedding(query_text)
                if qv:
                    # 使用同步方法（OpenSearch客户端是同步的）
                    vector_hits = self.os.search_document_vectors_sync(
                        query_vector=qv,
                        similarity_threshold=similarity_threshold,
                        limit=recall_limit,
                        knowledge_base_id=knowledge_base_id,
                        category_id=category_id
                    ) or []
                    logger.info(f"向量搜索完成，找到 {len(vector_hits)} 个结果")
        except Exception as e:
            logger.warning(f"向量检索失败: {e}")
        
        try:
            if use_keywords:
                logger.info(f"开始关键词搜索: {query_text[:50]}...")
                # 关键词检索：复用 OpenSearchService 的 client
                must: List[Dict[str, Any]] = [
                    {"match": {"content": {"query": query_text}}}
                ]
                if knowledge_base_id:
                    if isinstance(knowledge_base_id, list) and len(knowledge_base_id) > 0:
                        if len(knowledge_base_id) == 1:
                            must.append({"term": {"knowledge_base_id": knowledge_base_id[0]}})
                        else:
                            must.append({"terms": {"knowledge_base_id": knowledge_base_id}})
                    elif isinstance(knowledge_base_id, int):
                        must.append({"term": {"knowledge_base_id": knowledge_base_id}})
                if category_id is not None:
                    must.append({"term": {"category_id": category_id}})
                
                # 添加高亮配置
                highlight_config = self.os._build_highlight_config(query_text, fields=["content"])
                
                resp = self.os.client.search(
                    index=self.os.document_index,
                    body={
                        "query": {"bool": {"must": must}},
                        "size": recall_limit,
                        **highlight_config
                    },
                )
                keyword_hits = [
                    {
                        "chunk_id": h["_source"].get("chunk_id"),
                        "document_id": h["_source"].get("document_id"),
                        "knowledge_base_id": h["_source"].get("knowledge_base_id"),
                        "content": h["_source"].get("content"),
                        "chunk_type": h["_source"].get("chunk_type"),
                        "metadata": h["_source"].get("metadata") or {},
                        "bm25_score": h.get("_score", 0.0),
                        "similarity_score": h.get("_score", 0.0),  # 统一使用similarity_score
                        "highlighted_content": self.os._extract_highlight(h, "content"),  # 添加高亮内容
                    }
                    for h in resp.get("hits", {}).get("hits", [])
                ]
                logger.info(f"关键词搜索完成，找到 {len(keyword_hits)} 个结果")
        except Exception as e:
            logger.warning(f"关键词检索失败: {e}")
        
        # 融合向量搜索结果和关键词搜索结果
        by_id: Dict[int, Dict[str, Any]] = {}
        
        # 添加向量搜索结果
        for h in vector_hits:
            cid = h.get("chunk_id")
            if cid is None:
                continue
            by_id[cid] = {
                "chunk_id": cid,
                "document_id": h.get("document_id"),
                "knowledge_base_id": h.get("knowledge_base_id"),
                "content": h.get("content"),
                "chunk_type": h.get("chunk_type"),
                "metadata": h.get("metadata") or {},
                "knn_score": h.get("similarity_score", 0.0),
                "bm25_score": 0.0,
                "score": 0.0,  # 初始分数
                "highlighted_content": h.get("highlighted_content"),  # 保留高亮内容
            }
        
        # 添加关键词搜索结果并合并
        for h in keyword_hits:
            cid = h.get("chunk_id")
            if cid is None:
                continue
            item = by_id.get(cid)
            if item is None:
                by_id[cid] = {
                    "chunk_id": cid,
                    "document_id": h.get("document_id"),
                    "knowledge_base_id": h.get("knowledge_base_id"),
                    "content": h.get("content"),
                    "chunk_type": h.get("chunk_type", "text"),
                    "metadata": h.get("metadata") or {},
                    "knn_score": 0.0,
                    "bm25_score": h.get("bm25_score", 0.0),
                    "score": 0.0,
                    "highlighted_content": h.get("highlighted_content"),  # 保留高亮内容
                }
            else:
                item["bm25_score"] = h.get("bm25_score", 0.0)
                # 关键词搜索可能没有chunk_type，保留向量搜索的
                if not item.get("chunk_type") and h.get("chunk_type"):
                    item["chunk_type"] = h.get("chunk_type")
                if not item.get("metadata") and h.get("metadata"):
                    item["metadata"] = h.get("metadata") or {}
                # 优先使用关键词搜索的高亮内容（通常更准确）
                if h.get("highlighted_content"):
                    item["highlighted_content"] = h.get("highlighted_content")
        
        # 若未指定，使用配置的 α
        if alpha is None:
            try:
                alpha = float(getattr(settings, 'SEARCH_HYBRID_ALPHA', 0.6))
            except Exception:
                alpha = 0.6
        logger.info(f"混合搜索融合权重 α={alpha} (向量权重={alpha}, 关键词BM25权重={1-alpha})")

        # 计算融合分数（线性加权）
        for v in by_id.values():
            v["score"] = alpha * v.get("knn_score", 0.0) + (1 - alpha) * v.get("bm25_score", 0.0)
            results.append(v)
        logger.info(f"融合完成，去重后候选数量: {len(results)}, 向量召回: {len(vector_hits)}, 关键词BM25召回: {len(keyword_hits)}")
        
        # 初步排序（按融合分数）
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        # 使用Rerank模型进行精排（优化：合并关联图片的OCR文本）
        logger.info(f"开始Rerank精排，候选数量: {len(results)}, 返回数量: {top_k}")
        
        # 优化：为每个文本块添加关联图片的OCR文本，提升rerank效果
        enriched_results = await self._enrich_chunks_with_image_ocr(results)
        
        reranked_results = self.rerank_service.rerank(
            query=query_text,
            candidates=enriched_results,
            top_k=top_k
        )
        all_reranked_results = reranked_results[:]
        # 应用最小精排分（优先使用传入参数，否则使用全局配置）
        try:
            min_score = min_rerank_score if min_rerank_score is not None else float(getattr(settings, 'RERANK_MIN_SCORE', 0.0))
            logger.info(f"混合检索应用最小精排分: {min_score} (来源: {'请求参数' if min_rerank_score is not None else '全局配置'})")
            reranked_results = [r for r in reranked_results if (r.get('rerank_score') or r.get('score') or 0) >= float(min_score)]
            if not reranked_results and all_reranked_results:
                logger.info(
                    "精排分阈值过滤后结果为空，回退到未过滤的精排结果（避免完全无答案）。"
                )
                reranked_results = all_reranked_results
        except Exception:
            pass
        
        logger.info(f"混合搜索完成，Rerank后返回 {len(reranked_results)} 个结果（注：前端可能按min_rerank_score再次过滤）")
        return reranked_results
    
    async def search(self, search_request: SearchRequest) -> List[SearchResponse]:
        """搜索文档 - 支持关键词、语义、混合搜索、精确匹配 + Rerank精排"""
        try:
            logger.info(f"开始搜索: {search_request.query}, 类型: {search_request.search_type}")
            
            # 根据搜索类型调用不同的方法
            if search_request.search_type == "vector":
                results = await self.vector_search(search_request)
            elif search_request.search_type == "keyword":
                results = await self.keyword_search(search_request)
            elif search_request.search_type == "hybrid":
                results = await self.hybrid_search(search_request)
            elif search_request.search_type == "exact":
                results = await self.exact_search(search_request)
            else:
                # 默认使用混合搜索
                results = await self.hybrid_search(search_request)
            
            # 转换为SearchResponse格式（并尽量从metadata抽取表格结构）
            search_responses = []
            for result in results:
                meta = result.get("metadata") or {}
                if isinstance(meta, str):
                    try:
                        import json
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                # 优先根据编辑页的懒加载标记回填表格 cells
                table_cells = (meta or {}).get("cells")
                table_headers = (meta or {}).get("headers")
                table_rows = (meta or {}).get("rows")
                matrix = None
                if not table_cells and (table_headers or table_rows):
                    try:
                        matrix = [table_headers or []] + (table_rows or [])
                    except Exception:
                        matrix = None
                # 懒加载：table_group_uid / table_id
                if not table_cells:
                    group_uid = (meta or {}).get("table_group_uid")
                    table_uid = (meta or {}).get("table_id") or (meta or {}).get("table_uid")
                    loaded = {}
                    if group_uid:
                        loaded = self._load_table_by_group_uid(group_uid)
                    elif table_uid:
                        loaded = self._load_table_by_uid(table_uid)
                    # 再兜底：通过 (doc,chunk) 直接反查
                    if not loaded.get("cells"):
                        try:
                            loaded = self._hydrate_table_by_chunk(int(result.get("document_id")), int(result.get("chunk_id")))
                        except Exception:
                            loaded = {}
                    if loaded.get("cells"):
                        table_cells = loaded.get("cells")
                        table_headers = loaded.get("headers") or table_headers
                search_response = SearchResponse(
                    document_id=result.get("document_id"),
                    chunk_id=result.get("chunk_id"),
                    content=result.get("content", ""),
                    score=result.get("score", 0.0),
                    chunk_type=result.get("chunk_type") or (meta or {}).get("chunk_type"),
                    cells=table_cells,
                    matrix=matrix,
                    table=( {"headers": table_headers, "rows": table_rows} if (table_headers or table_rows) else None ),
                    # Rerank相关信息
                    rerank_score=result.get("rerank_score"),
                    has_image_ocr=result.get("has_image_ocr", False),
                    image_ocr_count=result.get("image_ocr_count", 0),
                    # 搜索结果高亮
                    highlighted_content=result.get("highlighted_content"),
                    metadata={
                        "knowledge_base_id": result.get("knowledge_base_id"),
                        "chunk_type": result.get("chunk_type"),
                        "knn_score": result.get("knn_score"),
                        "bm25_score": result.get("bm25_score"),
                        "rerank_score": result.get("rerank_score"),
                        "original_score": result.get("original_score"),
                    }
                )
                search_responses.append(search_response)
            
            logger.info(f"SearchService.search() 完成，转换为SearchResponse格式，最终返回前端 {len(search_responses)} 个结果")
            return search_responses
            
        except Exception as e:
            logger.error(f"搜索失败: {e}", exc_info=True)
            return []
    
    async def vector_search(self, search_request: SearchRequest) -> List[Dict[str, Any]]:
        """向量搜索 - 基于向量相似度的语义搜索 + Rerank精排"""
        try:
            logger.info(f"开始向量搜索: {search_request.query}")
            
            # 生成查询向量
            query_vector = self.vs.generate_embedding(search_request.query)
            if not query_vector:
                logger.warning("向量生成失败")
                return []
            
            # OpenSearch向量搜索（使用同步方法）
            results = self.os.search_document_vectors_sync(
                query_vector=query_vector,
                similarity_threshold=getattr(search_request, "similarity_threshold", settings.SEARCH_VECTOR_THRESHOLD),
                limit=(search_request.limit or settings.SEARCH_VECTOR_TOPK) * 3,  # 召回更多候选
                knowledge_base_id=search_request.knowledge_base_id,
                category_id=getattr(search_request, "category_id", None)
            ) or []
            
            # 添加分数字段
            for result in results:
                result["score"] = result.get("similarity_score", 0.0)
                result["knn_score"] = result.get("similarity_score", 0.0)
                result["bm25_score"] = 0.0
            
            # Rerank精排
            top_k = (search_request.limit or settings.SEARCH_VECTOR_TOPK or settings.RERANK_TOP_K)
            reranked_results = self.rerank_service.rerank(
                query=search_request.query,
                candidates=results,
                top_k=top_k
            )
            # 后端最小精排分过滤（保护：限制到[0.0,0.99]）
            req_min = getattr(search_request, 'min_rerank_score', None)
            min_score = req_min if req_min is not None else settings.RERANK_MIN_SCORE
            try:
                min_score = float(min_score)
            except Exception:
                min_score = settings.RERANK_MIN_SCORE
            if min_score < 0.0:
                min_score = 0.0
            if min_score >= 1.0:
                min_score = 0.99
            logger.info(f"向量检索应用最小精排分: {min_score} (请求值={req_min}, 默认={settings.RERANK_MIN_SCORE})")
            try:
                reranked_results = [r for r in reranked_results if (r.get('rerank_score') or r.get('score') or 0) >= float(min_score)]
            except Exception:
                pass
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}", exc_info=True)
            return []
    
    async def keyword_search(self, search_request: SearchRequest) -> List[Dict[str, Any]]:
        """关键词搜索 - 基于BM25的文本搜索 + Rerank精排"""
        try:
            logger.info(f"开始关键词搜索: {search_request.query}")
            
            # 构建关键词查询
            must: List[Dict[str, Any]] = [
                {"match": {"content": {"query": search_request.query}}}
            ]
            if search_request.knowledge_base_id:
                kb_ids = search_request.knowledge_base_id
                if isinstance(kb_ids, list) and len(kb_ids) > 0:
                    if len(kb_ids) == 1:
                        must.append({"term": {"knowledge_base_id": kb_ids[0]}})
                    else:
                        must.append({"terms": {"knowledge_base_id": kb_ids}})
                elif isinstance(kb_ids, int):
                    must.append({"term": {"knowledge_base_id": kb_ids}})
            if getattr(search_request, "category_id", None) is not None:
                must.append({"term": {"category_id": search_request.category_id}})
            
            # 执行搜索
            resp = self.os.client.search(
                index=self.os.document_index,
                body={
                    "query": {"bool": {"must": must}},
                    "size": search_request.limit * 3,  # 召回更多候选
                },
            )
            
            results = [
                {
                    "chunk_id": h["_source"].get("chunk_id"),
                    "document_id": h["_source"].get("document_id"),
                    "knowledge_base_id": h["_source"].get("knowledge_base_id"),
                    "content": h["_source"].get("content"),
                    "chunk_type": h["_source"].get("chunk_type"),
                    "metadata": h["_source"].get("metadata") or {},
                    "bm25_score": h.get("_score", 0.0),
                    "score": h.get("_score", 0.0),
                    "knn_score": 0.0,
                }
                for h in resp.get("hits", {}).get("hits", [])
            ]
            
            # Rerank精排
            top_k = (search_request.limit or settings.SEARCH_VECTOR_TOPK or settings.RERANK_TOP_K)
            reranked_results = self.rerank_service.rerank(
                query=search_request.query,
                candidates=results,
                top_k=top_k
            )
            # 后端最小精排分过滤（保护同上）
            req_min = getattr(search_request, 'min_rerank_score', None)
            min_score = req_min if req_min is not None else settings.RERANK_MIN_SCORE
            try:
                min_score = float(min_score)
            except Exception:
                min_score = settings.RERANK_MIN_SCORE
            if min_score < 0.0:
                min_score = 0.0
            if min_score >= 1.0:
                min_score = 0.99
            logger.info(f"关键词检索应用最小精排分: {min_score} (请求值={req_min}, 默认={settings.RERANK_MIN_SCORE})")
            try:
                reranked_results = [r for r in reranked_results if (r.get('rerank_score') or r.get('score') or 0) >= float(min_score)]
            except Exception:
                pass
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}", exc_info=True)
            return []
    
    async def exact_search(self, search_request: SearchRequest) -> List[Dict[str, Any]]:
        """精确匹配搜索 - 使用match_phrase查询"""
        try:
            # 服务层参数验证（防御性编程）
            if not search_request.query or not search_request.query.strip():
                logger.warning("精确匹配搜索：查询文本为空，返回空结果")
                return []
            
            logger.info(f"开始精确匹配搜索: {search_request.query}")
            
            # 使用OpenSearch的match_phrase查询
            # 合并分类过滤：仅当前端传入时生效
            merged_filters: Dict[str, Any] = {}
            if search_request.filters:
                try:
                    merged_filters.update(search_request.filters)
                except Exception:
                    pass
            category_id = getattr(search_request, "category_id", None)
            if category_id is not None and "category_id" not in merged_filters:
                merged_filters["category_id"] = category_id

            # OpenSearch已经按分数排序返回结果，不需要再次排序
            results = await self.os.search_document_exact_match(
                query_text=search_request.query,
                limit=search_request.limit,
                knowledge_base_id=search_request.knowledge_base_id,
                similarity_threshold=0.0,  # 精确匹配通常不设置阈值，但保留参数以便未来扩展
                filters=merged_filters or None,
                sort_by=search_request.sort_by,
                sort_order=search_request.sort_order or "desc",
                fields=getattr(settings, 'SEARCH_EXACT_FIELDS', ["content"])  # 支持多字段短语匹配
            )
            
            # 精确匹配不使用Rerank（因为已经是最精确的匹配）
            # OpenSearch已经按分数或指定字段排序，不需要再次排序
            
            logger.info(f"精确匹配搜索完成，返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"精确匹配搜索失败: {e}", exc_info=True)
            return []
    
    async def hybrid_search(self, search_request: SearchRequest) -> List[Dict[str, Any]]:
        """混合搜索 - 结合关键词和语义的混合检索 + Rerank精排"""
        try:
            logger.info(f"开始混合搜索: {search_request.query}")
            
            # 使用mixed_search方法（已实现融合逻辑）
            top_k = search_request.limit if search_request.limit > 0 else settings.RERANK_TOP_K
            
            results = await self.mixed_search(
                query_text=search_request.query,
                knowledge_base_id=search_request.knowledge_base_id,
                top_k=top_k,
                alpha=None,  # 使用配置的SEARCH_HYBRID_ALPHA
                use_keywords=True,
                use_vector=True,
                similarity_threshold=getattr(search_request, "similarity_threshold", None),  # None 时会使用配置值
                category_id=getattr(search_request, "category_id", None),
                min_rerank_score=getattr(search_request, "min_rerank_score", None)
            )
            
            return results
            
        except Exception as e:
            logger.error(f"混合搜索失败: {e}", exc_info=True)
            return []
    
    async def get_suggestions(self, request) -> List[str]:
        """获取搜索建议"""
        # TODO: 实现搜索建议逻辑
        return []
    
    async def get_search_history(self, user_id: Optional[int] = None, limit: int = 20):
        """获取搜索历史"""
        # TODO: 实现搜索历史逻辑
        return []
    
    async def save_search(self, save_request) -> Dict[str, Any]:
        """保存搜索"""
        # TODO: 实现保存搜索逻辑
        return {"message": "搜索已保存"}
    
    async def delete_search_history(self, history_id: int) -> None:
        """删除搜索历史"""
        # TODO: 实现删除搜索历史逻辑
        pass
    
    async def advanced_search(self, advanced_request) -> List[SearchResponse]:
        """高级搜索 - 支持复杂查询语法（布尔查询、通配符、正则表达式等）"""
        try:
            from app.schemas.search import SearchAdvancedRequest
            
            logger.info(f"开始高级搜索: {advanced_request.query[:50]}...")
            
            # 验证查询条件
            has_query = advanced_request.query and advanced_request.query.strip()
            has_bool = advanced_request.bool_query and advanced_request.bool_query.strip()
            has_exact = advanced_request.exact_phrase and advanced_request.exact_phrase.strip()
            has_wildcard = advanced_request.wildcard and advanced_request.wildcard.strip()
            has_regex = advanced_request.regex and advanced_request.regex.strip()
            
            if not any([has_query, has_bool, has_exact, has_wildcard, has_regex]):
                logger.warning("高级搜索：没有提供任何查询条件")
                return []
            
            # 构建filters（包含category_id等）
            filters = advanced_request.filters or {}
            if advanced_request.knowledge_base_id:
                # knowledge_base_id通过单独参数传递，不需要放在filters中
                pass
            
            # 调用OpenSearch高级搜索
            results = await self.os.search_document_advanced(
                query=advanced_request.query or "",
                bool_query=advanced_request.bool_query,
                exact_phrase=advanced_request.exact_phrase,
                wildcard=advanced_request.wildcard,
                regex=advanced_request.regex,
                limit=advanced_request.limit,
                knowledge_base_id=advanced_request.knowledge_base_id,
                filters=filters,
                similarity_threshold=0.0  # 高级搜索通常不设置阈值，或者可以通过filters传递
            )
            
            # 转换为SearchResponse格式（高级搜索也补齐表格结构）
            search_responses = []
            for result in results:
                meta = result.get("metadata") or {}
                if isinstance(meta, str):
                    try:
                        import json
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                table_cells = (meta or {}).get("cells")
                table_headers = (meta or {}).get("headers")
                table_rows = (meta or {}).get("rows")
                matrix = None
                if not table_cells and (table_headers or table_rows):
                    try:
                        matrix = [table_headers or []] + (table_rows or [])
                    except Exception:
                        matrix = None
                if not table_cells:
                    group_uid = (meta or {}).get("table_group_uid")
                    table_uid = (meta or {}).get("table_id") or (meta or {}).get("table_uid")
                    loaded = {}
                    if group_uid:
                        loaded = self._load_table_by_group_uid(group_uid)
                    elif table_uid:
                        loaded = self._load_table_by_uid(table_uid)
                    if loaded.get("cells"):
                        table_cells = loaded.get("cells")
                        table_headers = loaded.get("headers") or table_headers
                search_response = SearchResponse(
                    document_id=result.get("document_id"),
                    chunk_id=result.get("chunk_id"),
                    content=result.get("content", ""),
                    score=result.get("score", 0.0),
                    chunk_type=result.get("chunk_type") or (meta or {}).get("chunk_type"),
                    cells=table_cells,
                    matrix=matrix,
                    table=( {"headers": table_headers, "rows": table_rows} if (table_headers or table_rows) else None ),
                    rerank_score=None,  # 高级搜索不使用Rerank
                    has_image_ocr=False,
                    image_ocr_count=0,
                    metadata={
                        "knowledge_base_id": result.get("knowledge_base_id"),
                        "chunk_type": result.get("chunk_type"),
                        "knn_score": result.get("knn_score", 0.0),
                        "bm25_score": result.get("bm25_score", 0.0),
                        "original_score": result.get("original_score", 0.0),
                    }
                )
                search_responses.append(search_response)
            
            logger.info(f"高级搜索完成，返回 {len(search_responses)} 个结果")
            return search_responses
            
        except Exception as e:
            logger.error(f"高级搜索失败: {e}", exc_info=True)
            return []
    
    async def get_search_facets(self, query: str, knowledge_base_id: Optional[int] = None):
        """获取搜索分面信息"""
        # TODO: 实现分面搜索逻辑
        from app.schemas.search import SearchFacetsResponse
        return SearchFacetsResponse(facets={}, total=0)
    
    async def similar_search(self, similar_request):
        """相似搜索 - 基于文档相似度搜索"""
        # TODO: 实现相似搜索逻辑
        return []
    
    async def _enrich_chunks_with_image_ocr(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为文本块搜索结果添加关联图片的OCR文本，提升rerank效果
        
        Args:
            results: 搜索结果列表，每个结果包含 chunk_id, document_id, content 等字段
            
        Returns:
            增强后的结果列表，content字段包含原始文本+关联图片OCR文本
        """
        try:
            if not results:
                return results
            
            logger.debug(f"开始为 {len(results)} 个搜索结果添加关联图片OCR文本")
            
            doc_service = DocumentService(self.db)
            enriched_results = []
            
            for result in results:
                chunk_id = result.get("chunk_id")
                document_id = result.get("document_id")
                original_content = result.get("content", "")
                
                if not chunk_id or not document_id:
                    enriched_results.append(result)
                    continue
                
                try:
                    # 获取文本块关联的图片
                    from app.models.chunk import DocumentChunk
                    chunk = self.db.query(DocumentChunk).filter(
                        DocumentChunk.id == chunk_id
                    ).first()
                    
                    if chunk:
                        # 获取关联图片
                        associated_images = doc_service.get_images_for_chunk(document_id, chunk)
                        
                        # 收集图片OCR文本
                        ocr_texts = []
                        for img in associated_images:
                            if img.ocr_text and img.ocr_text.strip():
                                ocr_texts.append(img.ocr_text.strip())
                        
                        # 如果有OCR文本，合并到content中
                        if ocr_texts:
                            # 将OCR文本附加到原始内容后（用于rerank）
                            enriched_content = original_content
                            if ocr_texts:
                                ocr_suffix = "\n\n[图片文字]: " + " ".join(ocr_texts)
                                enriched_content = original_content + ocr_suffix
                            
                            # 更新content字段（用于rerank）
                            result["content"] = enriched_content
                            result["has_image_ocr"] = True
                            result["image_ocr_count"] = len(ocr_texts)
                            logger.debug(f"文本块 {chunk_id} 已添加 {len(ocr_texts)} 个图片的OCR文本")
                        else:
                            result["has_image_ocr"] = False
                            result["image_ocr_count"] = 0
                    else:
                        result["has_image_ocr"] = False
                        result["image_ocr_count"] = 0
                    
                except Exception as e:
                    logger.warning(f"为文本块 {chunk_id} 添加图片OCR文本失败: {e}")
                    # 失败时保持原样
                    result["has_image_ocr"] = False
                    result["image_ocr_count"] = 0
                
                enriched_results.append(result)
            
            logger.debug(f"完成OCR文本增强，共处理 {len(enriched_results)} 个结果")
            return enriched_results
            
        except Exception as e:
            logger.warning(f"OCR文本增强失败: {e}，返回原始结果")
            return results
