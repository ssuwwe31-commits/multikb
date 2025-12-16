"""
QA History Service
根据知识问答系统设计文档实现历史记录存储功能
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.config.settings import settings
from app.services.opensearch_service import OpenSearchService
from app.services.ollama_service import OllamaService
from app.core.exceptions import CustomException, ErrorCode

class QAHistoryService:
    """问答历史服务 - 根据设计文档实现"""
    
    def __init__(self, db: Session):
        self.db = db
        self.opensearch_service = OpenSearchService()
        self.ollama_service = OllamaService(db)
        
        # OpenSearch索引配置 - 根据设计文档
        self.INDEX_NAME = settings.QA_HISTORY_INDEX_NAME
        self.ANSWER_INDEX_NAME = getattr(settings, "QA_ANSWER_INDEX_NAME", "qa_answers")
        self.INDEX_MAPPING = {
            "mappings": {
                "properties": {
                    "question_id": {"type": "keyword"},
                    "session_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "knowledge_base_id": {"type": "integer"},
                    "question_content": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "answer_content": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "source_info": {"type": "object"},
                    "processing_info": {"type": "object"},
                    "quality_assessment": {"type": "object"},
                    "user_feedback": {"type": "object"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "question_vector": {
                        "type": "knn_vector",
                        "dimension": settings.TEXT_EMBEDDING_DIMENSION,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "answer_vector": {
                        "type": "knn_vector",
                        "dimension": settings.TEXT_EMBEDDING_DIMENSION,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "question_type": {"type": "keyword"},
                    "answer_quality": {"type": "float"},
                    "keywords": {"type": "keyword"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "ik_max_word": {
                            "type": "ik_max_word"
                        }
                    }
                }
            }
        }
        self.ANSWER_INDEX_MAPPING = {
            "mappings": {
                "properties": {
                    "question_id": {"type": "keyword"},
                    "session_id": {"type": "keyword"},
                    "knowledge_base_id": {"type": "integer"},
                    "question_content": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "answer_content": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "answer_strategy": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "source_ids": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "question_vector": {
                        "type": "knn_vector",
                        "dimension": settings.TEXT_EMBEDDING_DIMENSION,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "answer_vector": {
                        "type": "knn_vector",
                        "dimension": settings.TEXT_EMBEDDING_DIMENSION,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "ik_max_word": {
                            "type": "ik_max_word"
                        }
                    }
                }
            }
        }
    
    async def store_qa_history(
        self,
        question_id: str,
        session_id: str,
        user_id: str,
        knowledge_base_id: int,
        question_content: str,
        answer_content: str,
        source_info: List[Dict[str, Any]],
        processing_info: Dict[str, Any],
        quality_assessment: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        存储问答历史 - 根据设计文档实现
        
        Args:
            question_id: 问题ID
            session_id: 会话ID
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            question_content: 问题内容
            answer_content: 答案内容
            source_info: 来源信息
            processing_info: 处理信息
            quality_assessment: 质量评估
            user_feedback: 用户反馈
            
        Returns:
            存储是否成功
        """
        try:
            logger.info(f"开始存储问答历史，问题ID: {question_id}")
            
            # 1. 生成向量数据
            question_vector = await self._generate_question_vector(question_content)
            answer_vector = await self._generate_answer_vector(answer_content)
            
            # 2. 提取关键词
            keywords = await self._extract_keywords(question_content, answer_content)
            
            # 3. 清理 source_info，确保 document_id 为整数或 None（避免 OpenSearch 类型冲突）
            cleaned_source_info = []
            for src in source_info:
                cleaned_src = src.copy()
                doc_id = cleaned_src.get("document_id")
                # ✅ 如果 document_id 不是整数类型，设置为 None
                if doc_id is not None and not isinstance(doc_id, int):
                    # 尝试转换为整数，如果失败则设为 None
                    try:
                        cleaned_src["document_id"] = int(doc_id)
                    except (ValueError, TypeError):
                        cleaned_src["document_id"] = None
                cleaned_source_info.append(cleaned_src)
            
            # 4. 构建历史记录文档
            history_doc = {
                "question_id": question_id,
                "session_id": session_id,
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "question_content": question_content,
                "answer_content": answer_content,
                "source_info": cleaned_source_info,
                "processing_info": processing_info,
                "quality_assessment": quality_assessment,
                "user_feedback": user_feedback or {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "question_vector": question_vector,
                "answer_vector": answer_vector,
                "question_type": processing_info.get("input_type", "text"),
                "answer_quality": quality_assessment.get("overall_score", 0.0),
                "keywords": keywords
            }
            
            # 5. 存储到OpenSearch
            success = await self._store_to_opensearch(question_id, history_doc)

            # 6. 构建并存储答案索引文档（用于全文/语义检索）
            answer_doc = {
                "question_id": question_id,
                "session_id": session_id,
                "knowledge_base_id": knowledge_base_id,
                "question_content": question_content,
                "answer_content": answer_content,
                "answer_strategy": processing_info.get("answer_strategy"),
                "confidence": quality_assessment.get("confidence", 0.0),
                "source_ids": [src.get("document_id") for src in cleaned_source_info if src.get("document_id") is not None and isinstance(src.get("document_id"), int)],
                "keywords": keywords,
                "question_vector": question_vector,
                "answer_vector": answer_vector,
                "created_at": history_doc["created_at"],
                "updated_at": history_doc["updated_at"]
            }
            answer_index_success = await self._store_to_answer_index(question_id, answer_doc)
            if not answer_index_success:
                logger.warning(f"问答答案索引存储失败 question_id={question_id}")
            
            if success:
                logger.info(f"问答历史存储成功，问题ID: {question_id}")
            else:
                logger.error(f"问答历史存储失败，问题ID: {question_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"存储问答历史失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.HISTORY_STORAGE_FAILED,
                message=f"存储问答历史失败: {str(e)}"
            )
    
    async def get_qa_history(
        self,
        user_id: Optional[str] = None,
        knowledge_base_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        size: int = settings.QA_HISTORY_DEFAULT_PAGE_SIZE,
        search_keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户问答历史 - 根据设计文档实现
        
        Args:
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            size: 每页大小
            search_keyword: 搜索关键词
            
        Returns:
            历史记录列表
        """
        try:
            logger.info(f"获取问答历史，用户ID: {user_id}, 页码: {page}")
            
            # 构建查询条件
            query = self._build_history_query(
                user_id, knowledge_base_id, start_time, end_time, search_keyword
            )
            
            # 添加分页
            from_index = (page - 1) * size
            query["from"] = from_index
            query["size"] = size
            
            # 添加排序
            query["sort"] = [{"created_at": {"order": "desc"}}]
            
            # 执行查询
            results = await self.opensearch_service.search(self.INDEX_NAME, query)
            
            # 处理结果
            history_records = []
            for hit in results.get("hits", {}).get("hits", []):
                record = hit["_source"]
                record["id"] = hit["_id"]
                history_records.append(record)
            
            # 构建响应
            total_hits = results.get("hits", {}).get("total", {}).get("value", 0)
            total_pages = (total_hits + size - 1) // size
            
            response = {
                "history_records": history_records,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_hits,
                    "total_pages": total_pages
                },
                "statistics": {
                    "total_records": total_hits,
                    "answered_count": len([r for r in history_records if r.get("answer_content")]),
                    "unanswered_count": len([r for r in history_records if not r.get("answer_content")])
                }
            }
            
            logger.info(f"获取问答历史成功，返回 {len(history_records)} 条记录")
            return response
            
        except Exception as e:
            logger.error(f"获取问答历史失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.HISTORY_QUERY_FAILED,
                message=f"获取问答历史失败: {str(e)}"
            )
    
    async def search_qa_history(self, search_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        搜索历史问答 - 根据设计文档实现
        
        Args:
            search_request: 搜索请求
            
        Returns:
            搜索结果
        """
        try:
            logger.info(f"搜索历史问答，关键词: {search_request.get('search_keyword')}")
            
            search_keyword = search_request.get("search_keyword", "")
            search_type = search_request.get("search_type", "hybrid")
            filter_conditions = search_request.get("filter_conditions", {})
            sort_method = search_request.get("sort_method", "relevance")
            page = search_request.get("page", 1)
            size = search_request.get("size", settings.QA_HISTORY_DEFAULT_PAGE_SIZE)
            
            # 构建搜索查询
            if search_type == "keyword":
                query = self._build_keyword_search_query(search_keyword, filter_conditions)
            elif search_type == "semantic":
                query = self._build_semantic_search_query(search_keyword, filter_conditions)
            elif search_type == "hybrid":
                query = self._build_hybrid_search_query(search_keyword, filter_conditions)
            else:
                raise CustomException(
                    code=ErrorCode.INVALID_SEARCH_TYPE,
                    message=f"无效的搜索类型: {search_type}"
                )
            
            # 添加排序
            query["sort"] = self._build_sort_clause(sort_method)
            
            # 添加分页
            from_index = (page - 1) * size
            query["from"] = from_index
            query["size"] = size
            
            # 执行搜索
            results = await self.opensearch_service.search(self.INDEX_NAME, query)
            
            # 处理搜索结果
            search_results = []
            for hit in results.get("hits", {}).get("hits", []):
                record = hit["_source"]
                record["id"] = hit["_id"]
                record["relevance_score"] = hit.get("_score", 0.0)
                
                # 添加高亮信息
                if "highlight" in hit:
                    record["highlight"] = hit["highlight"]
                
                search_results.append(record)
            
            # 构建响应
            total_hits = results.get("hits", {}).get("total", {}).get("value", 0)
            total_pages = (total_hits + size - 1) // size
            
            response = {
                "search_results": search_results,
                "search_statistics": {
                    "total_results": total_hits,
                    "search_time": results.get("took", 0),
                    "search_type": search_type,
                    "search_keyword": search_keyword
                },
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_hits,
                    "total_pages": total_pages
                }
            }
            
            logger.info(f"搜索历史问答成功，找到 {len(search_results)} 个结果")
            return response
            
        except Exception as e:
            logger.error(f"搜索历史问答失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.HISTORY_SEARCH_FAILED,
                message=f"搜索历史问答失败: {str(e)}"
            )
    
    async def get_qa_detail(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        获取问答详情 - 根据设计文档实现
        
        Args:
            question_id: 问题ID
            
        Returns:
            问答详情
        """
        try:
            logger.info(f"获取问答详情，问题ID: {question_id}")
            
            # 构建查询
            query = {
                "query": {
                    "term": {
                        "question_id": question_id
                    }
                }
            }
            
            # 执行查询
            results = await self.opensearch_service.search(self.INDEX_NAME, query)
            
            # 处理结果
            hits = results.get("hits", {}).get("hits", [])
            if not hits:
                return None
            
            record = hits[0]["_source"]
            record["id"] = hits[0]["_id"]
            
            logger.info(f"获取问答详情成功，问题ID: {question_id}")
            return record
            
        except Exception as e:
            logger.error(f"获取问答详情失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.HISTORY_DETAIL_FAILED,
                message=f"获取问答详情失败: {str(e)}"
            )
    
    async def update_user_feedback(
        self,
        question_id: str,
        feedback: Dict[str, Any]
    ) -> bool:
        """
        更新用户反馈 - 根据设计文档实现
        
        Args:
            question_id: 问题ID
            feedback: 用户反馈
            
        Returns:
            更新是否成功
        """
        try:
            logger.info(f"更新用户反馈，问题ID: {question_id}")
            
            # 构建更新文档
            update_doc = {
                "user_feedback": feedback,
                "updated_at": datetime.now().isoformat()
            }
            
            # 执行更新
            success = await self.opensearch_service.update_document(
                self.INDEX_NAME, question_id, update_doc
            )
            
            if success:
                logger.info(f"用户反馈更新成功，问题ID: {question_id}")
            else:
                logger.error(f"用户反馈更新失败，问题ID: {question_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"更新用户反馈失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.FEEDBACK_UPDATE_FAILED,
                message=f"更新用户反馈失败: {str(e)}"
            )
    
    async def delete_qa_history(
        self,
        question_id: str
    ) -> bool:
        """
        删除问答历史 - 根据设计文档实现
        
        Args:
            question_id: 问题ID
            
        Returns:
            删除是否成功
        """
        try:
            logger.info(f"删除问答历史，问题ID: {question_id}")
            
            # 执行删除
            success = await self.opensearch_service.delete_document(
                self.INDEX_NAME, question_id
            )
            
            if success:
                logger.info(f"问答历史删除成功，问题ID: {question_id}")
            else:
                logger.error(f"问答历史删除失败，问题ID: {question_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除问答历史失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.HISTORY_DELETE_FAILED,
                message=f"删除问答历史失败: {str(e)}"
            )
    
    async def cleanup_old_history(
        self,
        days: int = settings.QA_HISTORY_CLEANUP_DAYS
    ) -> int:
        """
        清理过期历史数据 - 根据设计文档实现
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数量
        """
        try:
            logger.info(f"开始清理 {days} 天前的历史数据")
            
            # 计算过期时间
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 构建删除查询
            query = {
                "query": {
                    "range": {
                        "created_at": {
                            "lt": cutoff_time.isoformat()
                        }
                    }
                }
            }
            
            # 执行删除
            result = await self.opensearch_service.delete_by_query(
                self.INDEX_NAME, query
            )
            
            deleted_count = result.get("deleted", 0)
            logger.info(f"历史数据清理完成，删除了 {deleted_count} 条记录")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理历史数据失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.HISTORY_CLEANUP_FAILED,
                message=f"清理历史数据失败: {str(e)}"
            )
    
    # 辅助方法实现
    
    async def _generate_question_vector(self, question_content: str) -> List[float]:
        """生成问题向量"""
        try:
            vector = await self.ollama_service.generate_embedding(question_content)
            return vector
        except Exception as e:
            logger.error(f"生成问题向量失败: {e}")
            return [0.0] * settings.TEXT_EMBEDDING_DIMENSION
    
    async def _generate_answer_vector(self, answer_content: str) -> List[float]:
        """生成答案向量"""
        try:
            vector = await self.ollama_service.generate_embedding(answer_content)
            return vector
        except Exception as e:
            logger.error(f"生成答案向量失败: {e}")
            return [0.0] * settings.TEXT_EMBEDDING_DIMENSION
    
    async def _extract_keywords(self, question_content: str, answer_content: str) -> List[str]:
        """提取关键词"""
        try:
            # 简单的关键词提取
            combined_text = f"{question_content} {answer_content}"
            words = combined_text.split()
            
            # 过滤停用词
            stop_words = {"的", "是", "在", "有", "和", "the", "is", "in", "and", "a", "an"}
            keywords = [word for word in words if word not in stop_words and len(word) > 1]
            
            return keywords[:settings.MULTIMODAL_MAX_KEYWORDS]  # 返回前N个关键词
            
        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
            return []
    
    async def _store_to_opensearch(self, question_id: str, history_doc: Dict[str, Any]) -> bool:
        """存储到OpenSearch"""
        try:
            # 确保索引存在
            await self._ensure_index_exists()
            
            # 存储文档
            success = await self.opensearch_service.index_document(
                self.INDEX_NAME, question_id, history_doc
            )
            
            return success
            
        except Exception as e:
            logger.error(f"存储到OpenSearch失败: {e}")
            return False

    async def _store_to_answer_index(self, question_id: str, answer_doc: Dict[str, Any]) -> bool:
        """存储到问答答案索引"""
        try:
            await self._ensure_answer_index_exists()
            return await self.opensearch_service.index_document(
                self.ANSWER_INDEX_NAME, question_id, answer_doc
            )
        except Exception as e:
            logger.error(f"存储答案索引失败: {e}")
            return False
    
    async def _ensure_index_exists(self):
        """确保索引存在"""
        try:
            exists = await self.opensearch_service.index_exists(self.INDEX_NAME)
            if not exists:
                await self.opensearch_service.create_index(
                    self.INDEX_NAME, self.INDEX_MAPPING
                )
                logger.info(f"创建索引: {self.INDEX_NAME}")
        except Exception as e:
            logger.error(f"确保索引存在失败: {e}")

    async def _ensure_answer_index_exists(self):
        """确保问答答案索引存在"""
        try:
            exists = await self.opensearch_service.index_exists(self.ANSWER_INDEX_NAME)
            if not exists:
                await self.opensearch_service.create_index(
                    self.ANSWER_INDEX_NAME, self.ANSWER_INDEX_MAPPING
                )
                logger.info(f"创建索引: {self.ANSWER_INDEX_NAME}")
        except Exception as e:
            logger.error(f"确保答案索引存在失败: {e}")
    
    def _build_history_query(
        self,
        user_id: Optional[str],
        knowledge_base_id: Optional[int],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        search_keyword: Optional[str]
    ) -> Dict[str, Any]:
        """构建历史查询"""
        query = {"query": {"bool": {"must": []}}}
        
        # 用户ID过滤
        if user_id:
            query["query"]["bool"]["must"].append({
                "term": {"user_id": user_id}
            })
        
        # 知识库ID过滤
        if knowledge_base_id:
            query["query"]["bool"]["must"].append({
                "term": {"knowledge_base_id": knowledge_base_id}
            })
        
        # 时间范围过滤
        if start_time or end_time:
            time_range = {}
            if start_time:
                time_range["gte"] = start_time.isoformat()
            if end_time:
                time_range["lte"] = end_time.isoformat()
            
            query["query"]["bool"]["must"].append({
                "range": {"created_at": time_range}
            })
        
        # 关键词搜索
        if search_keyword:
            query["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": search_keyword,
                    "fields": ["question_content", "answer_content"],
                    "type": "best_fields"
                }
            })
        
        return query
    
    def _build_keyword_search_query(
        self,
        search_keyword: str,
        filter_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建关键词搜索查询"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": search_keyword,
                                "fields": ["question_content", "answer_content"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "question_content": {},
                    "answer_content": {}
                }
            }
        }
        
        # 添加过滤条件
        self._add_filter_conditions(query, filter_conditions)
        
        return query
    
    def _build_semantic_search_query(
        self,
        search_keyword: str,
        filter_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建语义搜索查询"""
        # 生成搜索向量
        search_vector = self._generate_search_vector(search_keyword)
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "field": "question_vector",
                                "query_vector": search_vector,
                                "k": 10,
                                "num_candidates": settings.QA_DEFAULT_MAX_RESULTS
                            }
                        }
                    ]
                }
            }
        }
        
        # 添加过滤条件
        self._add_filter_conditions(query, filter_conditions)
        
        return query
    
    def _build_hybrid_search_query(
        self,
        search_keyword: str,
        filter_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建混合搜索查询"""
        # 生成搜索向量
        search_vector = self._generate_search_vector(search_keyword)
        
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": search_keyword,
                                "fields": ["question_content", "answer_content"],
                                "type": "best_fields",
                                "boost": 1.0
                            }
                        },
                        {
                            "knn": {
                                "field": "question_vector",
                                "query_vector": search_vector,
                                "k": 10,
                                "num_candidates": settings.QA_DEFAULT_MAX_RESULTS,
                                "boost": 1.5
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "highlight": {
                "fields": {
                    "question_content": {},
                    "answer_content": {}
                }
            }
        }
        
        # 添加过滤条件
        self._add_filter_conditions(query, filter_conditions)
        
        return query
    
    def _add_filter_conditions(self, query: Dict[str, Any], filter_conditions: Dict[str, Any]):
        """添加过滤条件"""
        if not filter_conditions:
            return
        
        if "must" not in query["query"]["bool"]:
            query["query"]["bool"]["must"] = []
        
        # 用户ID过滤
        if "user_id" in filter_conditions:
            query["query"]["bool"]["must"].append({
                "term": {"user_id": filter_conditions["user_id"]}
            })
        
        # 知识库ID过滤
        if "knowledge_base_id" in filter_conditions:
            query["query"]["bool"]["must"].append({
                "term": {"knowledge_base_id": filter_conditions["knowledge_base_id"]}
            })
        
        # 时间范围过滤
        if "time_range" in filter_conditions:
            time_range = filter_conditions["time_range"]
            query["query"]["bool"]["must"].append({
                "range": {"created_at": time_range}
            })
        
        # 问答质量过滤
        if "answer_quality" in filter_conditions:
            quality_range = filter_conditions["answer_quality"]
            query["query"]["bool"]["must"].append({
                "range": {"answer_quality": quality_range}
            })
    
    def _build_sort_clause(self, sort_method: str) -> List[Dict[str, Any]]:
        """构建排序子句"""
        if sort_method == "time":
            return [{"created_at": {"order": "desc"}}]
        elif sort_method == "quality":
            return [{"answer_quality": {"order": "desc"}}]
        elif sort_method == "relevance":
            return [{"_score": {"order": "desc"}}]
        else:
            return [{"created_at": {"order": "desc"}}]
    
    def _generate_search_vector(self, search_keyword: str) -> List[float]:
        """生成搜索向量"""
        try:
            # 这里应该调用实际的向量生成服务
            # 为了演示，返回默认向量
            return [0.0] * settings.TEXT_EMBEDDING_DIMENSION
        except Exception as e:
            logger.error(f"生成搜索向量失败: {e}")
            return [0.0] * settings.TEXT_EMBEDDING_DIMENSION
