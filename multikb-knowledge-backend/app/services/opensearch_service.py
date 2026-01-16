"""
OpenSearch Service
根据文档处理流程设计实现OpenSearch集成功能
"""

from typing import List, Optional, Dict, Any
import asyncio
import json
import threading
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.helpers import bulk as os_bulk
from opensearchpy.exceptions import OpenSearchException
from app.config.settings import settings
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode

class OpenSearchService:
    """OpenSearch服务 - 严格按照设计文档实现（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(OpenSearchService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化OpenSearch客户端（仅执行一次）"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self.client = self._create_client()
            self.document_index = settings.DOCUMENT_INDEX_NAME
            self.image_index = settings.IMAGE_INDEX_NAME
            self.qa_index = settings.QA_INDEX_NAME
            self.qa_answer_index = getattr(settings, "QA_ANSWER_INDEX_NAME", "qa_answers")
            self.resource_events_index = getattr(settings, "RESOURCE_EVENTS_INDEX_NAME", "resource_events")
            self.external_search_index = getattr(settings, "EXTERNAL_SEARCH_INDEX_NAME", "external_searches")
            self._ensure_indices_exist()
            self._initialized = True
    
    def _create_client(self) -> OpenSearch:
        """创建OpenSearch客户端"""
        try:
            logger.info("创建OpenSearch客户端")
            
            # 根据设计文档的OpenSearch配置
            client = OpenSearch(
                hosts=[settings.OPENSEARCH_URL],
                use_ssl=settings.OPENSEARCH_USE_SSL,
                verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            logger.info("OpenSearch客户端创建成功")
            return client
            
        except Exception as e:
            logger.error(f"创建OpenSearch客户端失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_CONNECTION_FAILED,
                message=f"OpenSearch连接失败: {str(e)}"
            )
    
    def _ensure_indices_exist(self):
        """确保索引存在 - 根据设计文档的索引设计"""
        try:
            logger.info("检查并创建OpenSearch索引")
            
            # 创建/校验文档内容索引（校验向量维度，若不一致则重建）
            if not self.client.indices.exists(index=self.document_index):
                self._create_document_index()
            else:
                try:
                    mapping = self.client.indices.get_mapping(index=self.document_index)
                    props = mapping[self.document_index]["mappings"].get("properties", {})
                    content_vector = props.get("content_vector", {})
                    current_dim = content_vector.get("dimension")
                    from app.config.settings import settings as _settings
                    want_dim = int(getattr(_settings, "TEXT_EMBEDDING_DIMENSION", 768))
                    if current_dim and current_dim != want_dim:
                        logger.warning(
                            f"检测到 content_vector 维度不一致，当前={current_dim} 期望={want_dim}，将删除并重建索引 {self.document_index}"
                        )
                        self.client.indices.delete(index=self.document_index, ignore=[400, 404])
                        self._create_document_index()
                    # 兜底：若 knn 未开启，则在线开启
                    try:
                        settings_res = self.client.indices.get_settings(index=self.document_index)
                        knn_flag = settings_res.get(self.document_index, {}).get('settings', {}).get('index', {}).get('knn')
                        if not (str(knn_flag).lower() == 'true'):
                            self.client.indices.put_settings(index=self.document_index, body={"index.knn": True})
                            logger.info(f"文档索引检测到 knn 未开启，已自动开启: {self.document_index}")
                        else:
                            logger.info(f"文档索引 knn 已开启: {self.document_index}")
                    except Exception as _e:
                        logger.warning(f"文档索引 knn 设置检查/开启失败: {_e}")
                except Exception:
                    # 若映射读取失败，尽量继续
                    pass
            
            # 创建图片专用索引
            if not self.client.indices.exists(index=self.image_index):
                self._create_image_index()
            else:
                # 兜底：若 knn 未开启，则在线开启
                try:
                    settings_res = self.client.indices.get_settings(index=self.image_index)
                    knn_flag = settings_res.get(self.image_index, {}).get('settings', {}).get('index', {}).get('knn')
                    if not (str(knn_flag).lower() == 'true'):
                        self.client.indices.put_settings(index=self.image_index, body={"index.knn": True})
                        logger.info(f"图片索引检测到 knn 未开启，已自动开启: {self.image_index}")
                    else:
                        logger.info(f"图片索引 knn 已开启: {self.image_index}")
                except Exception as _e:
                    logger.warning(f"图片索引 knn 设置检查/开启失败: {_e}")
            
            # 创建问答历史索引
            if not self.client.indices.exists(index=self.qa_index):
                self._create_qa_index()

            # 创建问答答案索引
            if not self.client.indices.exists(index=self.qa_answer_index):
                self._create_qa_answer_index()
            
            # 创建资源事件索引
            if not self.client.indices.exists(index=self.resource_events_index):
                self._create_resource_events_index()

            # 创建外部搜索索引
            if not self.client.indices.exists(index=self.external_search_index):
                self._create_external_search_index()
            
            logger.info("OpenSearch索引检查完成")
            
        except Exception as e:
            logger.error(f"创建OpenSearch索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"OpenSearch索引创建失败: {str(e)}"
            )

    async def index_exists(self, index: str) -> bool:
        """异步检查索引是否存在"""
        loop = asyncio.get_running_loop()

        def _exists() -> bool:
            return bool(self.client.indices.exists(index=index))

        try:
            return await loop.run_in_executor(None, _exists)
        except Exception as e:
            logger.error(f"[OpenSearch] index_exists error index={index}: {e}")
            raise

    async def create_index(self, index: str, mapping: Dict[str, Any]) -> bool:
        """异步创建索引（若不存在）"""
        loop = asyncio.get_running_loop()

        def _create() -> bool:
            if self.client.indices.exists(index=index):
                return True
            self.client.indices.create(index=index, body=mapping)
            return True

        try:
            return await loop.run_in_executor(None, _create)
        except Exception as e:
            logger.error(f"[OpenSearch] create_index error index={index}: {e}")
            raise

    async def index_document(self, index: str, doc_id: str, document: Dict[str, Any]) -> bool:
        """异步写入文档"""
        loop = asyncio.get_running_loop()

        def _index() -> bool:
            resp = self.client.index(index=index, id=doc_id, body=document, refresh=True)
            result = resp.get("result")
            return result in ("created", "updated")

        try:
            return await loop.run_in_executor(None, _index)
        except Exception as e:
            logger.error(f"[OpenSearch] index_document error index={index} id={doc_id}: {e}")
            raise
    
    async def search(self, index: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """异步搜索文档 - 通用搜索方法"""
        loop = asyncio.get_running_loop()
        
        def _search() -> Dict[str, Any]:
            return self.client.search(index=index, body=query)
        
        try:
            return await loop.run_in_executor(None, _search)
        except Exception as e:
            logger.error(f"[OpenSearch] search error index={index}: {e}")
            raise
    
    async def delete_by_query(self, index: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """异步按查询条件删除文档"""
        loop = asyncio.get_running_loop()
        
        def _delete_by_query() -> Dict[str, Any]:
            return self.client.delete_by_query(index=index, body=query, refresh=True)
        
        try:
            return await loop.run_in_executor(None, _delete_by_query)
        except Exception as e:
            logger.error(f"[OpenSearch] delete_by_query error index={index}: {e}")
            raise
    
    def _create_document_index(self):
        """创建文档内容索引 - 根据设计文档实现"""
        try:
            logger.info(f"创建文档索引: {self.document_index}")
            
            # 根据设计文档的索引配置
            index_mapping = {
                "settings": {
                    "number_of_shards": settings.OPENSEARCH_NUMBER_OF_SHARDS,
                    "number_of_replicas": settings.OPENSEARCH_NUMBER_OF_REPLICAS,
                    # 关键：开启 KNN（用于 content_vector）
                    "index.knn": True,
                    "analysis": {
                        "analyzer": {
                            "ik_max_word": {
                                "type": settings.TEXT_ANALYZER
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        # 基础字段
                        "document_id": {"type": "integer"},
                        "knowledge_base_id": {"type": "integer"},
                        "category_id": {"type": "integer"},
                        "chunk_id": {"type": "integer"},
                        
                        # 内容字段
                        "content": {
                            "type": "text",
                            "analyzer": settings.TEXT_ANALYZER,
                            "search_analyzer": settings.TEXT_ANALYZER
                        },
                        "chunk_type": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "metadata": {"type": "text"},
                        
                        # 时间字段
                        "created_at": {"type": "date"},
                        
                        # 向量字段 - 文本向量（维度来自配置），HNSW算法
                        "content_vector": {
                            "type": "knn_vector",
                            "dimension": settings.TEXT_EMBEDDING_DIMENSION,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": settings.HNSW_EF_CONSTRUCTION,
                                    "m": settings.HNSW_M
                                }
                            }
                        },
                        
                        # 图片字段
                        "image_info": {
                            "type": "object",
                            "properties": {
                                "image_id": {"type": "integer"},
                                "image_path": {"type": "keyword"},
                                "page_number": {"type": "integer"},
                                "coordinates": {"type": "object"},
                                "image_type": {"type": "keyword"},
                                "ocr_text": {"type": "text"},
                                "description": {"type": "text"}
                            }
                        }
                    }
                }
            }
            
            self.client.indices.create(index=self.document_index, body=index_mapping)
            logger.info(f"文档索引创建成功: {self.document_index}，已设置 index.knn=true，向量字段=content_vector，维度={settings.TEXT_EMBEDDING_DIMENSION}")
            try:
                settings_res = self.client.indices.get_settings(index=self.document_index)
                knn_flag = settings_res.get(self.document_index, {}).get('settings', {}).get('index', {}).get('knn')
                logger.info(f"文档索引当前 knn 设置: {knn_flag}")
            except Exception as _e:
                logger.warning(f"读取文档索引 settings 失败: {_e}")
            
        except Exception as e:
            logger.error(f"创建文档索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"文档索引创建失败: {str(e)}"
            )
    
    def _create_image_index(self):
        """创建图片专用索引 - 根据设计文档实现"""
        try:
            logger.info(f"创建图片索引: {self.image_index}")
            
            # 根据设计文档的图片索引配置
            index_mapping = {
                "settings": {
                    "number_of_shards": settings.OPENSEARCH_NUMBER_OF_SHARDS,
                    "number_of_replicas": settings.OPENSEARCH_NUMBER_OF_REPLICAS,
                    # 关键：开启 KNN（用于 content_vector）
                    "index.knn": True
                },
                "mappings": {
                    "properties": {
                        # 基础字段
                        "image_id": {"type": "integer"},
                        "document_id": {"type": "integer"},
                        "knowledge_base_id": {"type": "integer"},
                        "category_id": {"type": "integer"},
                        # 元素顺序索引（用于前端100%还原）
                        "element_index": {"type": "integer"},
                        
                        # 图片字段
                        "image_path": {"type": "keyword"},
                        "page_number": {"type": "integer"},
                        "coordinates": {"type": "object"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                        "image_type": {"type": "keyword"},
                        
                        # 内容字段
                        "ocr_text": {
                            "type": "text",
                            "analyzer": settings.TEXT_ANALYZER
                        },
                        "description": {"type": "text"},
                        "feature_tags": {"type": "keyword"},
                        
                        # 向量字段 - 512维图片向量，HNSW算法
                        "image_vector": {
                            "type": "knn_vector",
                            "dimension": settings.IMAGE_EMBEDDING_DIMENSION,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": settings.HNSW_EF_CONSTRUCTION,
                                    "m": settings.HNSW_M
                                }
                            }
                        },
                        
                        # 时间字段
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        
                        # 元数据字段
                        "metadata": {"type": "object"},
                        "processing_status": {"type": "keyword"},
                        "model_version": {"type": "keyword"}
                    }
                }
            }
            
            self.client.indices.create(index=self.image_index, body=index_mapping)
            logger.info(f"图片索引创建成功: {self.image_index}，已设置 index.knn=true，向量字段=image_vector，维度=512")
            try:
                settings_res = self.client.indices.get_settings(index=self.image_index)
                knn_flag = settings_res.get(self.image_index, {}).get('settings', {}).get('index', {}).get('knn')
                logger.info(f"图片索引当前 knn 设置: {knn_flag}")
            except Exception as _e:
                logger.warning(f"读取图片索引 settings 失败: {_e}")
            
        except Exception as e:
            logger.error(f"创建图片索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"图片索引创建失败: {str(e)}"
            )
    
    def _create_qa_index(self):
        """创建问答历史索引 - 根据设计文档实现"""
        try:
            logger.info(f"创建问答历史索引: {self.qa_index}")

            from app.config.settings import settings as _settings

            index_mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "index.knn": True,
                    "analysis": {
                        "analyzer": {
                            "ik_max_word": {
                                "type": "ik_max_word"
                            }
                        }
                    }
                },
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
                            "dimension": _settings.TEXT_EMBEDDING_DIMENSION,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib"
                            }
                        },
                        "answer_vector": {
                            "type": "knn_vector",
                            "dimension": _settings.TEXT_EMBEDDING_DIMENSION,
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
                }
            }

            self.client.indices.create(index=self.qa_index, body=index_mapping)
            logger.info(f"问答历史索引创建成功: {self.qa_index}")

        except Exception as e:
            logger.error(f"创建问答历史索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"问答历史索引创建失败: {str(e)}"
            )

    def _create_qa_answer_index(self):
        """创建问答答案索引"""
        try:
            logger.info(f"创建问答答案索引: {self.qa_answer_index}")

            from app.config.settings import settings as _settings

            index_mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "index.knn": True,
                    "analysis": {
                        "analyzer": {
                            "ik_max_word": {"type": "ik_max_word"}
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "question_id": {"type": "keyword"},
                        "session_id": {"type": "keyword"},
                        "knowledge_base_id": {"type": "integer"},
                        "question_content": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "answer_content": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        "answer_strategy": {"type": "keyword"},
                        "confidence": {"type": "float"},
                        "keywords": {"type": "keyword"},
                        "source_ids": {"type": "keyword"},
                        "question_vector": {
                            "type": "knn_vector",
                            "dimension": _settings.TEXT_EMBEDDING_DIMENSION,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib"
                            }
                        },
                        "answer_vector": {
                            "type": "knn_vector",
                            "dimension": _settings.TEXT_EMBEDDING_DIMENSION,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib"
                            }
                        }
                    }
                }
            }

            self.client.indices.create(index=self.qa_answer_index, body=index_mapping)
            logger.info(f"问答答案索引创建成功: {self.qa_answer_index}")

        except Exception as e:
            logger.error(f"创建问答答案索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"问答答案索引创建失败: {str(e)}"
            )

    def _create_resource_events_index(self):
        """创建资源事件索引"""
        try:
            logger.info(f"创建资源事件索引: {self.resource_events_index}")

            index_mapping = {
                "settings": {
                    "number_of_shards": settings.OPENSEARCH_NUMBER_OF_SHARDS,
                    "number_of_replicas": settings.OPENSEARCH_NUMBER_OF_REPLICAS,
                },
                "mappings": {
                    "properties": {
                        "cluster_id": {"type": "integer"},
                        "resource_type": {"type": "keyword"},
                        "namespace": {"type": "keyword"},
                        "resource_uid": {"type": "keyword"},
                        "event_type": {"type": "keyword"},
                        "diff": {"type": "object", "enabled": True},
                        "created_at": {"type": "date"},
                    }
                }
            }

            self.client.indices.create(index=self.resource_events_index, body=index_mapping)
            logger.info(f"资源事件索引创建成功: {self.resource_events_index}")

        except Exception as e:
            logger.error(f"创建资源事件索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"资源事件索引创建失败: {str(e)}"
            )

    def _create_external_search_index(self):
        """创建外部搜索索引"""
        try:
            logger.info(f"创建外部搜索索引: {self.external_search_index}")

            index_mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "analysis": {
                        "analyzer": {
                            "ik_max_word": {
                                "type": settings.TEXT_ANALYZER
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "question": {"type": "text", "analyzer": settings.TEXT_ANALYZER},
                        "search_query": {"type": "text", "analyzer": settings.TEXT_ANALYZER},
                        "summary": {"type": "text", "analyzer": settings.TEXT_ANALYZER},
                        "session_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "from_cache": {"type": "boolean"},
                        "latency": {"type": "float"},
                        "metadata": {"type": "object"},
                        "results": {"type": "object"},
                        "created_at": {"type": "date"},
                    }
                }
            }

            self.client.indices.create(index=self.external_search_index, body=index_mapping)
            logger.info(f"外部搜索索引创建成功: {self.external_search_index}")
        except Exception as e:
            logger.error(f"创建外部搜索索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"外部搜索索引创建失败: {str(e)}"
            )

    async def ensure_resource_events_index(self) -> None:
        """确保 resource_events 索引存在（异步方法）"""
        try:
            exists = await self.index_exists(self.resource_events_index)
            if not exists:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._create_resource_events_index)
                logger.info(f"资源事件索引已创建: {self.resource_events_index}")
        except Exception as e:
            logger.warning(f"确保资源事件索引存在失败: {e}")

    async def index_resource_event(self, event_id: int, event_data: Dict[str, Any]) -> bool:
        """索引资源事件到 OpenSearch"""
        try:
            return await self.index_document(
                index=self.resource_events_index,
                doc_id=str(event_id),
                document=event_data,
            )
        except Exception as e:
            logger.warning(f"索引资源事件到 OpenSearch 失败: {e}")
            return False

    async def search_resource_events(
        self,
        cluster_id: int,
        resource_type: Optional[str] = None,
        namespace: Optional[str] = None,
        resource_uid: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """查询资源变更事件（OpenSearch）"""
        try:
            # 构建查询条件
            must_clauses = [{"term": {"cluster_id": cluster_id}}]
            
            if resource_type:
                must_clauses.append({"term": {"resource_type": resource_type}})
            if namespace:
                must_clauses.append({"term": {"namespace": namespace}})
            if resource_uid:
                must_clauses.append({"term": {"resource_uid": resource_uid}})
            if event_type:
                must_clauses.append({"term": {"event_type": event_type}})
            
            # 时间范围查询
            if start_time or end_time:
                range_query = {}
                if start_time:
                    range_query["gte"] = start_time
                if end_time:
                    range_query["lte"] = end_time
                must_clauses.append({"range": {"created_at": range_query}})
            
            query = {
                "bool": {
                    "must": must_clauses
                }
            }
            
            search_body = {
                "query": query,
                "size": min(limit, 1000),  # 限制最多 1000 条
                "sort": [{"created_at": {"order": "desc"}}],
            }
            
            loop = asyncio.get_running_loop()
            
            def _search() -> Dict[str, Any]:
                response = self.client.search(
                    index=self.resource_events_index,
                    body=search_body,
                )
                return response
            
            result = await loop.run_in_executor(None, _search)
            
            # 格式化返回结果
            hits = result.get("hits", {}).get("hits", [])
            events = []
            for hit in hits:
                source = hit.get("_source", {})
                events.append({
                    "id": hit.get("_id"),
                    **source
                })
            
            return {
                "total": result.get("hits", {}).get("total", {}).get("value", 0),
                "events": events,
            }
        except Exception as e:
            logger.warning(f"OpenSearch 查询资源事件失败: {e}")
            raise
    
    async def index_document_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """索引文档分块 - 根据设计文档实现"""
        try:
            logger.info(f"开始索引文档分块: {chunk_data.get('chunk_id')}")
            
            # 构建索引文档
            doc = {
                "document_id": chunk_data["document_id"],
                "knowledge_base_id": chunk_data["knowledge_base_id"],
                "category_id": chunk_data.get("category_id"),
                "chunk_id": chunk_data["chunk_id"],
                "content": chunk_data["content"],
                "chunk_type": chunk_data.get("chunk_type", "text"),
                "tags": chunk_data.get("tags", []),
                "metadata": json.dumps(chunk_data.get("metadata", {})),
                "created_at": chunk_data.get("created_at"),
            }
            # 可选写入向量
            if isinstance(chunk_data.get("content_vector"), list) and chunk_data["content_vector"]:
                doc["content_vector"] = chunk_data["content_vector"]
            
            # 如果有图片信息，添加图片字段
            if chunk_data.get("image_info"):
                doc["image_info"] = chunk_data["image_info"]
            
            # 索引到OpenSearch
            response = self.client.index(
                index=self.document_index,
                id=f"chunk_{chunk_data['chunk_id']}",
                body=doc,
                refresh="wait_for"
            )
            
            logger.info(f"文档分块索引成功: {chunk_data.get('chunk_id')}")
            return True
            
        except Exception as e:
            logger.error(f"文档分块索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"文档分块索引失败: {str(e)}"
            )

    # 同步封装，供 Celery 同步任务直接调用
    def index_document_chunk_sync(self, chunk_data: Dict[str, Any]) -> bool:
        body = {
            "document_id": chunk_data["document_id"],
            "knowledge_base_id": chunk_data["knowledge_base_id"],
            "category_id": chunk_data.get("category_id"),
            "chunk_id": chunk_data["chunk_id"],
            "content": chunk_data["content"],
            "chunk_type": chunk_data.get("chunk_type", "text"),
            "tags": chunk_data.get("tags", []),
            "metadata": json.dumps(chunk_data.get("metadata", {})),
            "created_at": chunk_data.get("created_at"),
        }
        if isinstance(chunk_data.get("content_vector"), list) and chunk_data["content_vector"]:
            body["content_vector"] = chunk_data["content_vector"]
        if chunk_data.get("image_info"):
            body["image_info"] = chunk_data["image_info"]
        self.client.index(
            index=self.document_index,
            id=f"chunk_{chunk_data['chunk_id']}",
            body=body,
            refresh="wait_for",
        )
        return True

    def bulk_index_document_chunks_sync(self, docs: List[Dict[str, Any]]) -> int:
        """批量索引分块，返回成功条数。"""
        actions = []
        for d in docs:
            src = {
                "document_id": d["document_id"],
                "knowledge_base_id": d["knowledge_base_id"],
                "category_id": d.get("category_id"),
                "chunk_id": d["chunk_id"],
                "content": d["content"],
                "chunk_type": d.get("chunk_type", "text"),
                "tags": d.get("tags", []),
                "metadata": json.dumps(d.get("metadata", {})),
                "created_at": d.get("created_at"),
            }
            if isinstance(d.get("content_vector"), list) and d["content_vector"]:
                src["content_vector"] = d["content_vector"]
            if d.get("image_info"):
                src["image_info"] = d["image_info"]
            actions.append({
                "_index": self.document_index,
                "_id": f"chunk_{d['chunk_id']}",
                "_source": src,
            })
        success, _ = os_bulk(self.client, actions, refresh=False)
        logger.info(f"批量索引分块完成: {success} 条")
        return success
    
    async def index_image(self, image_data: Dict[str, Any]) -> bool:
        """索引图片 - 根据设计文档实现"""
        try:
            logger.info(f"开始索引图片: {image_data.get('image_id')}")
            
            # 构建索引文档
            doc = {
                "image_id": image_data["image_id"],
                "document_id": image_data["document_id"],
                "knowledge_base_id": image_data["knowledge_base_id"],
                "category_id": image_data.get("category_id"),
                "image_path": image_data["image_path"],
                "page_number": image_data.get("page_number"),
                "coordinates": image_data.get("coordinates"),
                "width": image_data.get("width"),
                "height": image_data.get("height"),
                "image_type": image_data.get("image_type", "unknown"),
                "ocr_text": image_data.get("ocr_text", ""),
                "description": image_data.get("description", ""),
                "feature_tags": image_data.get("feature_tags", []),
                "image_vector": image_data["image_vector"],
                "created_at": image_data.get("created_at"),
                "updated_at": image_data.get("updated_at"),
                # 映射中 metadata 是 object，必须传 dict 而不是字符串
                "metadata": image_data.get("metadata", {}),
                "processing_status": image_data.get("processing_status", "completed"),
                "model_version": image_data.get("model_version", "1.0")
            }
            
            # 索引到OpenSearch
            response = self.client.index(
                index=self.image_index,
                id=f"image_{image_data['image_id']}",
                body=doc,
                refresh="wait_for"
            )
            
            logger.info(f"图片索引成功: {image_data.get('image_id')}")
            return True
            
        except Exception as e:
            logger.error(f"图片索引失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_INDEX_FAILED,
                message=f"图片索引失败: {str(e)}"
            )

    # 同步封装
    def index_image_sync(self, image_data: Dict[str, Any]) -> bool:
        self.client.index(
            index=self.image_index,
            id=f"image_{image_data['image_id']}",
            body={
                "image_id": image_data["image_id"],
                "document_id": image_data["document_id"],
                "knowledge_base_id": image_data["knowledge_base_id"],
                "category_id": image_data.get("category_id"),
                "image_path": image_data["image_path"],
                "page_number": image_data.get("page_number"),
                "coordinates": image_data.get("coordinates"),
                "width": image_data.get("width"),
                "height": image_data.get("height"),
                "image_type": image_data.get("image_type", "unknown"),
                "ocr_text": image_data.get("ocr_text", ""),
                "description": image_data.get("description", ""),
                "feature_tags": image_data.get("feature_tags", []),
                "image_vector": image_data["image_vector"],
                "created_at": image_data.get("created_at"),
                "updated_at": image_data.get("updated_at"),
                # 传递 dict 类型，符合 OpenSearch 映射中的 object
                "metadata": image_data.get("metadata", {}),
                "processing_status": image_data.get("processing_status", "completed"),
                "model_version": image_data.get("model_version", "1.0"),
            },
            refresh="wait_for",
        )
        return True
    
    def search_document_vectors_sync(
        self,
        query_vector: List[float],
        similarity_threshold: float | None = None,
        limit: int = 10,
        knowledge_base_id: Optional[List[int]] = None,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """搜索文档向量（同步版本）- 根据设计文档实现"""
        try:
            # 兜底阈值：优先使用入参，否则读取配置
            if similarity_threshold is None:
                from app.config.settings import settings as _settings
                similarity_threshold = float(getattr(_settings, "SEARCH_VECTOR_THRESHOLD", 0.0))
            logger.info(f"开始文档向量搜索（同步），相似度阈值: {similarity_threshold}")
            
            # 兼容/校验：query_vector 必须是 float 数组，避免 OS 报 x_content_parse_exception
            try:
                # 字符串 -> JSON
                if isinstance(query_vector, str):
                    import json as _json
                    query_vector = _json.loads(query_vector)
                # numpy -> list
                try:
                    import numpy as _np
                    if isinstance(query_vector, _np.ndarray):
                        query_vector = query_vector.tolist()
                except Exception:
                    pass
                # 元素转 float
                if isinstance(query_vector, list):
                    query_vector = [float(x) for x in query_vector]
            except Exception as _ve:
                logger.warning(f"查询向量格式修正失败，将返回空结果: {_ve}")
                return []
            if not isinstance(query_vector, list) or not query_vector:
                logger.warning("查询向量为空或格式错误，返回空结果")
                return []
            if not all(isinstance(x, (int, float)) for x in query_vector):
                logger.warning("查询向量元素非数值类型，返回空结果")
                return []

            # 构建过滤条件
            filters = []
            if knowledge_base_id:
                if isinstance(knowledge_base_id, list) and len(knowledge_base_id) > 0:
                    if len(knowledge_base_id) == 1:
                        filters.append({"term": {"knowledge_base_id": knowledge_base_id[0]}})
                    else:
                        filters.append({"terms": {"knowledge_base_id": knowledge_base_id}})
                elif isinstance(knowledge_base_id, int):
                    filters.append({"term": {"knowledge_base_id": knowledge_base_id}})
            if category_id is not None:
                filters.append({"term": {"category_id": category_id}})

            # 移除详细的向量值日志，减少日志量（只在 DEBUG 级别记录维度）
            # try:
            #     from app.core.logging import logger as _lg
            #     _lg.debug(
            #         f"[KNN] index={self.document_index}, dim={len(query_vector)}, "
            #         f"kb_id={knowledge_base_id}, category_id={category_id}"
            #     )
            # except Exception:
            #     pass

            # 2.11 官方稳态语法：顶层 knn + field/query_vector，filter 仅在存在时添加
            # 按 OpenSearch k-NN plugin 固定语法：content_vector + vector（不要 values/field/query_vector）
            knn_query = {
                "content_vector": {
                    "vector": query_vector,
                    "k": limit
                }
            }
            
            # 如果有过滤条件，使用 bool 查询包装 knn 查询
            if filters:
                body = {
                    "size": limit,
                    "query": {
                        "bool": {
                            "must": [
                                {"knn": knn_query}
                            ],
                            "filter": filters
                        }
                    }
                }
            else:
                body = {
                    "size": limit,
                    "query": {
                        "knn": knn_query
                    }
                }

            # 强制标准 JSON 序列化-反序列化，避免任何非基元类型导致被当作字符串
            try:
                import json as _json
                body_json = _json.dumps(body, ensure_ascii=False, separators=(",", ":"))
                logger.info(f"[KNN][body_first200]={body_json[:200]}")
                body = _json.loads(body_json)
            except Exception:
                pass

            try:
                response = self.client.search(index=self.document_index, body=body)
            except Exception as e_primary:
                # 兼容分支：部分集群要求 query_vector 使用 {"values": [...]} 包装
                try:
                    import copy as _copy, json as _json
                    alt_body = _copy.deepcopy(body)
                    qv = alt_body["query"]["knn"].pop("query_vector", None)
                    alt_body["query"]["knn"]["query_vector"] = {"values": qv if isinstance(qv, list) else []}
                    alt_json = _json.dumps(alt_body, ensure_ascii=False, separators=(",", ":"))
                    logger.info(f"[KNN][compat_values][body_first200]={alt_json[:200]}")
                    response = self.client.search(index=self.document_index, body=alt_body)
                except Exception:
                    raise e_primary
            
            # 处理搜索结果
            results = []
            for hit in response["hits"]["hits"]:
                if hit["_score"] >= similarity_threshold:
                    result = {
                        "chunk_id": hit["_source"]["chunk_id"],
                        "document_id": hit["_source"]["document_id"],
                        "knowledge_base_id": hit["_source"]["knowledge_base_id"],
                        "content": hit["_source"]["content"],
                        "similarity_score": hit["_score"],
                        "chunk_type": hit["_source"].get("chunk_type"),
                        "image_info": hit["_source"].get("image_info")
                    }
                    results.append(result)
            
            logger.info(f"文档向量搜索完成（同步），找到 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"文档向量搜索失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_SEARCH_FAILED,
                message=f"文档向量搜索失败: {str(e)}"
            )
    
    async def search_document_vectors(
        self,
        query_vector: List[float],
        similarity_threshold: Optional[float] = None,
        limit: int = 10,
        knowledge_base_id: Optional[List[int]] = None,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """搜索文档向量（异步版本）- 根据设计文档实现"""
        # 异步版本直接调用同步版本（OpenSearch客户端是同步的）
        return self.search_document_vectors_sync(
            query_vector=query_vector,
            similarity_threshold=similarity_threshold,
            limit=limit,
            knowledge_base_id=knowledge_base_id,
            category_id=category_id
        )
    
    async def search_image_vectors(
        self,
        query_vector: List[float],
        similarity_threshold: Optional[float] = None,
        limit: int | None = None,
        knowledge_base_id: Optional[List[int]] = None,
        exclude_image_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """搜索图片向量 - 根据设计文档实现"""
        try:
            if similarity_threshold is None:
                similarity_threshold = settings.SEARCH_VECTOR_THRESHOLD
            if not limit:
                limit = settings.SEARCH_VECTOR_TOPK
            logger.info(f"开始图片向量搜索，相似度阈值: {similarity_threshold}")
            
            # 确保 query_vector 是正确的类型（List[float]）
            import json
            try:
                # 如果 query_vector 是字符串，先解析
                if isinstance(query_vector, str):
                    query_vector = json.loads(query_vector)
                # 如果是 numpy 数组或其他类型，转换为列表
                if hasattr(query_vector, 'tolist'):
                    query_vector = query_vector.tolist()
                # 确保是列表且元素是浮点数
                query_vector = [float(x) for x in query_vector]
                # 移除详细的向量值日志，只记录维度
                logger.debug(f"[Image KNN] 向量维度: {len(query_vector)}")
            except Exception as e:
                logger.error(f"[Image KNN] query_vector 类型转换失败: {e}, 类型: {type(query_vector)}")
                raise CustomException(
                    code=ErrorCode.VECTOR_GENERATION_FAILED,
                    message=f"图片向量格式错误: {str(e)}"
                )
            
            # 构建搜索查询（使用 OpenSearch k-NN plugin 标准语法）
            # 重要：k 值应该略大于 limit，并配置 num_candidates 提升召回稳定性
            # 经验策略：
            # - k = max(limit * 2, 20)，最多 100，保证返回结果数量充足
            # - num_candidates = max(k * 3, 60)，最多 300，提升 HNSW 搜索的稳定性
            if limit:
                k_value = max(limit * 2, 20)
            else:
                k_value = 40
            k_value = min(k_value, 100)
            logger.info(
                f"[Image KNN] limit={limit}, k={k_value}, "
                f"similarity_threshold={similarity_threshold}"
            )
            knn_payload: Dict[str, Any] = {
                "vector": query_vector,
                "k": k_value
            }
            
            # 构建过滤条件（在 OpenSearch 查询层过滤，提高性能）
            filter_clauses = []
            if knowledge_base_id is not None:
                if isinstance(knowledge_base_id, list) and len(knowledge_base_id) > 0:
                    if len(knowledge_base_id) == 1:
                        filter_clauses.append({"term": {"knowledge_base_id": knowledge_base_id[0]}})
                    else:
                        filter_clauses.append({"terms": {"knowledge_base_id": knowledge_base_id}})
                elif isinstance(knowledge_base_id, int):
                    filter_clauses.append({"term": {"knowledge_base_id": knowledge_base_id}})
            if exclude_image_id:
                filter_clauses.append({"bool": {"must_not": [{"term": {"image_id": exclude_image_id}}]}})
            
            body: Dict[str, Any] = {
                "size": k_value,
                "query": {
                    "knn": {
                        "image_vector": knn_payload
                    }
                }
            }
            
            # 如果有过滤条件，添加到查询中
            if filter_clauses:
                body["query"] = {
                    "bool": {
                        "must": [{"knn": {"image_vector": knn_payload}}],
                        "filter": filter_clauses
                    }
                }
            
            # 强制标准 JSON 序列化-反序列化，确保 query_vector 是数组而不是字符串
            try:
                body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
                logger.debug(f"[Image KNN][body_first200]={body_json[:200]}")
                body = json.loads(body_json)
            except Exception as e:
                logger.warning(f"[Image KNN] JSON 序列化失败: {e}")
            
            # 执行搜索
            response = self.client.search(
                index=self.image_index,
                body=body
            )
            
            # 处理搜索结果
            results = []
            total_hits = len(response["hits"]["hits"])
            filtered_count = 0
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                # 严格按阈值过滤：只有 >= threshold 的结果才保留
                if score >= similarity_threshold:
                    source = hit["_source"]
                    # 注意：知识库和图片排除过滤已在 OpenSearch 查询层完成，这里不需要再次过滤
                    # 但如果 OpenSearch 版本不支持在 knn 查询中使用 filter，则保留这里的过滤逻辑作为兜底
                    result = {
                        "image_id": source["image_id"],
                        "document_id": source["document_id"],
                        "knowledge_base_id": source["knowledge_base_id"],
                        "image_path": source["image_path"],
                        "similarity_score": score,
                        "image_type": source.get("image_type"),
                        "page_number": source.get("page_number"),
                        "coordinates": source.get("coordinates"),
                        "ocr_text": source.get("ocr_text", ""),
                        "description": source.get("description", ""),
                        "source_document": str(source.get("document_id", ""))  # 转换为字符串，TODO: 获取文档名称
                    }
                    results.append(result)
                else:
                    filtered_count += 1
            
            # 限制返回数量（不超过 limit）
            if limit and len(results) > limit:
                results = results[:limit]
            
            logger.info(
                f"图片向量搜索完成：召回 {total_hits} 个候选，"
                f"阈值过滤（>={similarity_threshold}）后 {len(results)} 个结果，"
                f"过滤掉 {filtered_count} 个低分结果"
            )
            return results
            
        except Exception as e:
            logger.error(f"图片向量搜索失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_SEARCH_FAILED,
                message=f"图片向量搜索失败: {str(e)}"
            )
    
    async def search_image_keywords(
        self,
        query_text: str,
        limit: int = 10,
        knowledge_base_id: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """搜索图片关键词 - 根据设计文档实现"""
        try:
            logger.info(f"开始图片关键词搜索: {query_text}")
            
            # 构建搜索查询
            query = {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "ocr_text": {
                                    "query": query_text,
                                    "boost": 2.0
                                }
                            }
                        },
                        {
                            "match": {
                                "description": {
                                    "query": query_text,
                                    "boost": 1.5
                                }
                            }
                        },
                        {
                            "match": {
                                "feature_tags": {
                                    "query": query_text,
                                    "boost": 1.0
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
            
            # 添加知识库过滤
            if knowledge_base_id:
                if isinstance(knowledge_base_id, list) and len(knowledge_base_id) > 0:
                    if len(knowledge_base_id) == 1:
                        query["bool"]["filter"] = [
                            {"term": {"knowledge_base_id": knowledge_base_id[0]}}
                        ]
                    else:
                        query["bool"]["filter"] = [
                            {"terms": {"knowledge_base_id": knowledge_base_id}}
                        ]
                elif isinstance(knowledge_base_id, int):
                    query["bool"]["filter"] = [
                        {"term": {"knowledge_base_id": knowledge_base_id}}
                    ]
            
            # 执行搜索
            response = self.client.search(
                index=self.image_index,
                body={"query": query},
                size=limit
            )
            
            # 处理搜索结果
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "image_id": hit["_source"]["image_id"],
                    "document_id": hit["_source"]["document_id"],
                    "knowledge_base_id": hit["_source"]["knowledge_base_id"],
                    "image_path": hit["_source"]["image_path"],
                    "keyword_score": hit["_score"],
                    "image_type": hit["_source"].get("image_type"),
                    "page_number": hit["_source"].get("page_number"),
                    "coordinates": hit["_source"].get("coordinates"),
                    "ocr_text": hit["_source"].get("ocr_text", ""),
                    "description": hit["_source"].get("description", ""),
                    "source_document": str(hit["_source"].get("document_id", ""))  # 转换为字符串，TODO: 获取文档名称
                }
                results.append(result)
            
            logger.info(f"图片关键词搜索完成，找到 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"图片关键词搜索失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.OPENSEARCH_SEARCH_FAILED,
                message=f"图片关键词搜索失败: {str(e)}"
            )
    
    async def search_document_exact_match(
        self,
        query_text: str,
        limit: int = None,
        knowledge_base_id: Optional[List[int]] = None,
        similarity_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """精确匹配搜索 - 使用match_phrase查询"""
        try:
            # 验证查询文本
            if not query_text or not query_text.strip():
                logger.warning("精确匹配搜索：查询文本为空，返回空结果")
                return []
            
            # 验证limit参数
            if not limit or limit <= 0:
                limit = settings.SEARCH_VECTOR_TOPK
            elif limit > 1000:
                limit = 1000
                logger.warning(f"精确匹配搜索：limit参数过大，已限制为1000")
            
            logger.info(f"开始精确匹配搜索: {query_text[:50]}...，fields={fields or settings.SEARCH_EXACT_FIELDS}")
            
            # 构建查询
            # 若指定多个字段，则使用 multi_match type=phrase；否则使用 match_phrase
            target_fields = fields or getattr(settings, "SEARCH_EXACT_FIELDS", ["content"]) or ["content"]
            if isinstance(target_fields, str):
                target_fields = [target_fields]
            if len(target_fields) > 1:
                match_phrase_query = {
                    "multi_match": {
                        "query": query_text,
                        "type": "phrase",
                        "fields": target_fields
                    }
                }
            else:
                match_phrase_query = {
                    "match_phrase": {
                        target_fields[0]: {
                            "query": query_text,
                            "slop": 0
                        }
                    }
                }
            
            # 构建过滤条件
            filter_list = []
            if knowledge_base_id:
                if isinstance(knowledge_base_id, list) and len(knowledge_base_id) > 0:
                    if len(knowledge_base_id) == 1:
                        filter_list.append({"term": {"knowledge_base_id": knowledge_base_id[0]}})
                    else:
                        filter_list.append({"terms": {"knowledge_base_id": knowledge_base_id}})
                elif isinstance(knowledge_base_id, int):
                    filter_list.append({"term": {"knowledge_base_id": knowledge_base_id}})
            
            # 添加自定义filters
            if filters:
                filter_list.extend(self._build_filters(filters))
            
            # 构建最终查询
            if filter_list:
                query = {
                    "bool": {
                        "must": [match_phrase_query],
                        "filter": filter_list
                    }
                }
            else:
                query = match_phrase_query
            
            # 构建搜索体
            search_body = {
                "query": query,
                "size": limit,
                "_source": ["document_id", "chunk_id", "content", "chunk_type", "metadata", "knowledge_base_id"]
            }
            
            # 添加高亮配置
            highlight_config = self._build_highlight_config(query_text, fields=["content"])
            search_body.update(highlight_config)
            
            # 构建排序（只有在需要自定义排序时才添加）
            if sort_by:
                # 验证sort_order
                order = "desc" if sort_order.lower() == "desc" else "asc"
                search_body["sort"] = [{sort_by: {"order": order}}]
            # 如果没有指定sort_by，OpenSearch默认按_score排序，不需要显式指定
            
            response = self.client.search(
                index=self.document_index,
                body=search_body
            )
            
            # 处理结果
            results = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                if score >= similarity_threshold:
                    # 解析metadata字段
                    metadata_str = hit["_source"].get("metadata", "{}")
                    try:
                        metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                    
                    # 提取高亮内容
                    highlighted_content = self._extract_highlight(hit, "content")
                    
                    results.append({
                        "document_id": hit["_source"].get("document_id"),
                        "chunk_id": hit["_source"].get("chunk_id"),
                        "knowledge_base_id": hit["_source"].get("knowledge_base_id"),
                        "content": hit["_source"].get("content", ""),
                        "chunk_type": hit["_source"].get("chunk_type", "text"),
                        "metadata": metadata,
                        "score": score,
                        "bm25_score": score,  # match_phrase使用BM25评分
                        "original_score": score,
                        "knn_score": 0.0,  # 精确匹配不使用向量搜索
                        "highlighted_content": highlighted_content  # 添加高亮内容
                    })
            
            logger.info(f"精确匹配搜索完成，找到 {len(results)} 个结果")
            return results
            
        except OpenSearchException as e:
            logger.error(f"精确匹配搜索失败（OpenSearch异常）: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"精确匹配搜索失败: {e}", exc_info=True)
            return []
    
    def _build_highlight_config(self, query_text: str, fields: List[str] = None) -> Dict[str, Any]:
        """构建高亮配置
        
        Args:
            query_text: 查询文本
            fields: 要高亮的字段列表，默认为 ["content"]
        
        Returns:
            highlight 配置字典
        """
        if fields is None:
            fields = ["content"]
        
        return {
            "highlight": {
                "fields": {
                    field: {
                        "fragment_size": 150,
                        "number_of_fragments": 3,
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"]
                    }
                    for field in fields
                },
                "require_field_match": False
            }
        }
    
    def _extract_highlight(self, hit: Dict[str, Any], field: str = "content") -> Optional[str]:
        """从搜索结果中提取高亮内容
        
        Args:
            hit: OpenSearch 返回的 hit 对象
            field: 字段名，默认为 "content"
        
        Returns:
            高亮后的内容，如果没有高亮则返回 None
        """
        highlight = hit.get("highlight", {})
        if not highlight:
            return None
        
        # 获取字段的高亮片段
        field_highlights = highlight.get(field, [])
        if field_highlights:
            # 返回第一个高亮片段（通常是最相关的）
            return field_highlights[0]
        
        return None
    
    def _build_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """构建OpenSearch过滤条件
        
        Args:
            filters: 过滤条件字典，支持以下格式：
                - {"field": value} - term查询
                - {"field": {"gte": value}} - range查询
                - {"field": {"in": [value1, value2]}} - terms查询
        
        Returns:
            OpenSearch过滤条件列表
        """
        filter_list = []
        
        for field, condition in filters.items():
            if isinstance(condition, dict):
                # 处理range查询
                if any(key in condition for key in ["gte", "gt", "lte", "lt"]):
                    filter_list.append({"range": {field: condition}})
                # 处理terms查询（in操作）
                elif "in" in condition:
                    filter_list.append({"terms": {field: condition["in"]}})
                # 处理其他复杂条件
                else:
                    filter_list.append({"term": {field: condition}})
            else:
                # 简单term查询
                filter_list.append({"term": {field: condition}})
        
            return filter_list
    
    async def search_document_advanced(
        self,
        query: str,
        bool_query: Optional[str] = None,
        exact_phrase: Optional[str] = None,
        wildcard: Optional[str] = None,
        regex: Optional[str] = None,
        limit: int = 10,
        knowledge_base_id: Optional[List[int]] = None,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """高级搜索 - 支持布尔查询、通配符、正则表达式等复杂查询语法"""
        try:
            logger.info(f"开始高级搜索: {query[:50]}...")
            
            # 验证limit参数
            if limit <= 0:
                limit = 10
            elif limit > 1000:
                limit = 1000
                logger.warning(f"高级搜索：limit参数过大，已限制为1000")
            
            # 构建查询条件
            must_clauses = []
            should_clauses = []
            must_not_clauses = []
            
            # 1. 处理基础查询（query）
            if query and query.strip():
                must_clauses.append({"match": {"content": {"query": query}}})
            
            # 2. 处理布尔查询（bool_query）
            # 格式：支持简单的 AND/OR/NOT 语法
            # 例如："(MongoDB AND 连接) OR (Redis AND 配置)" 或 "MongoDB NOT 错误"
            if bool_query and bool_query.strip():
                bool_queries = self._parse_bool_query(bool_query)
                if bool_queries.get("must"):
                    must_clauses.extend(bool_queries["must"])
                if bool_queries.get("should"):
                    should_clauses.extend(bool_queries["should"])
                if bool_queries.get("must_not"):
                    must_not_clauses.extend(bool_queries["must_not"])
            
            # 3. 处理精确短语（exact_phrase）
            if exact_phrase and exact_phrase.strip():
                must_clauses.append({
                    "match_phrase": {
                        "content": {
                            "query": exact_phrase,
                            "slop": 0
                        }
                    }
                })
            
            # 4. 处理通配符查询（wildcard）
            if wildcard and wildcard.strip():
                must_clauses.append({
                    "wildcard": {
                        "content": {
                            "value": wildcard,
                            "boost": 1.0
                        }
                    }
                })
            
            # 5. 处理正则表达式查询（regex）
            if regex and regex.strip():
                # 移除regex字符串两端的斜杠（如果存在）
                regex_pattern = regex.strip()
                if regex_pattern.startswith('/') and regex_pattern.endswith('/'):
                    regex_pattern = regex_pattern[1:-1]
                
                must_clauses.append({
                    "regexp": {
                        "content": {
                            "value": regex_pattern,
                            "flags": "ALL",
                            "boost": 1.0
                        }
                    }
                })
            
            # 构建最终查询
            bool_query_dict = {}
            if must_clauses:
                bool_query_dict["must"] = must_clauses
            if should_clauses:
                bool_query_dict["should"] = should_clauses
                bool_query_dict["minimum_should_match"] = 1
            if must_not_clauses:
                bool_query_dict["must_not"] = must_not_clauses
            
            # 构建过滤条件
            filter_list = []
            if knowledge_base_id:
                if isinstance(knowledge_base_id, list) and len(knowledge_base_id) > 0:
                    if len(knowledge_base_id) == 1:
                        filter_list.append({"term": {"knowledge_base_id": knowledge_base_id[0]}})
                    else:
                        filter_list.append({"terms": {"knowledge_base_id": knowledge_base_id}})
                elif isinstance(knowledge_base_id, int):
                    filter_list.append({"term": {"knowledge_base_id": knowledge_base_id}})
            if filters:
                filter_list.extend(self._build_filters(filters))
            
            if filter_list:
                bool_query_dict["filter"] = filter_list
            
            # 如果没有查询条件，返回空结果
            if not bool_query_dict:
                logger.warning("高级搜索：没有有效的查询条件")
                return []
            
            query_body = {"bool": bool_query_dict}
            
            # 执行搜索
            search_body = {
                "query": query_body,
                "size": limit,
                "_source": ["document_id", "chunk_id", "content", "chunk_type", "metadata", "knowledge_base_id"]
            }
            
            # 添加高亮配置（如果有查询文本）
            query_text_for_highlight = query or exact_phrase or bool_query
            if query_text_for_highlight:
                highlight_config = self._build_highlight_config(query_text_for_highlight, fields=["content"])
                search_body.update(highlight_config)
            
            response = self.client.search(
                index=self.document_index,
                body=search_body
            )
            
            # 处理结果
            results = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                if score >= similarity_threshold:
                    # 解析metadata字段
                    metadata_str = hit["_source"].get("metadata", "{}")
                    try:
                        metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                    
                    # 提取高亮内容
                    highlighted_content = self._extract_highlight(hit, "content") if query_text_for_highlight else None
                    
                    results.append({
                        "document_id": hit["_source"].get("document_id"),
                        "chunk_id": hit["_source"].get("chunk_id"),
                        "knowledge_base_id": hit["_source"].get("knowledge_base_id"),
                        "content": hit["_source"].get("content", ""),
                        "chunk_type": hit["_source"].get("chunk_type", "text"),
                        "metadata": metadata,
                        "score": score,
                        "bm25_score": score,
                        "original_score": score,
                        "knn_score": 0.0,
                        "highlighted_content": highlighted_content  # 添加高亮内容
                    })
            
            logger.info(f"高级搜索完成，找到 {len(results)} 个结果")
            return results
            
        except OpenSearchException as e:
            logger.error(f"高级搜索失败（OpenSearch异常）: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"高级搜索失败: {e}", exc_info=True)
            return []
    
    def _parse_bool_query(self, bool_query: str) -> Dict[str, List[Dict[str, Any]]]:
        """解析布尔查询字符串
        
        支持格式：
        - "MongoDB AND 连接" -> must: [MongoDB, 连接]
        - "MongoDB OR Redis" -> should: [MongoDB, Redis]
        - "MongoDB NOT 错误" -> must: [MongoDB], must_not: [错误]
        - "(MongoDB AND 连接) OR (Redis AND 配置)" -> 复杂组合
        
        Args:
            bool_query: 布尔查询字符串
        
        Returns:
            包含must、should、must_not的字典
        """
        result = {"must": [], "should": [], "must_not": []}
        
        try:
            # 简单的布尔查询解析（支持 AND、OR、NOT）
            # 更复杂的语法可以通过递归解析括号实现，这里先实现简单版本
            
            # 处理NOT查询
            if " NOT " in bool_query.upper():
                parts = bool_query.split(" NOT ", 1)
                if len(parts) == 2:
                    # 必须包含parts[0]，不包含parts[1]
                    if parts[0].strip():
                        result["must"].append({"match": {"content": {"query": parts[0].strip()}}})
                    if parts[1].strip():
                        result["must_not"].append({"match": {"content": {"query": parts[1].strip()}}})
                    return result
            
            # 处理OR查询
            if " OR " in bool_query.upper():
                parts = bool_query.split(" OR ")
                for part in parts:
                    part = part.strip()
                    if part:
                        # 检查是否包含AND
                        if " AND " in part.upper():
                            and_parts = part.split(" AND ")
                            must_items = []
                            for and_part in and_parts:
                                and_part = and_part.strip()
                                if and_part:
                                    must_items.append({"match": {"content": {"query": and_part}}})
                            if must_items:
                                result["must"].append({"bool": {"must": must_items}})
                        else:
                            result["should"].append({"match": {"content": {"query": part}}})
                return result
            
            # 处理AND查询
            if " AND " in bool_query.upper():
                parts = bool_query.split(" AND ")
                for part in parts:
                    part = part.strip()
                    if part:
                        result["must"].append({"match": {"content": {"query": part}}})
                return result
            
            # 默认作为must查询
            if bool_query.strip():
                result["must"].append({"match": {"content": {"query": bool_query.strip()}}})
            
        except Exception as e:
            logger.warning(f"布尔查询解析失败，使用默认查询: {e}")
            # 解析失败时，使用原始查询作为must
            if bool_query.strip():
                result["must"].append({"match": {"content": {"query": bool_query.strip()}}})
        
        return result
    
    async def get_image_vector(self, image_id: int) -> Optional[List[float]]:
        """获取图片向量"""
        try:
            response = self.client.get(
                index=self.image_index,
                id=f"image_{image_id}"
            )
            
            return response["_source"].get("image_vector")
            
        except Exception as e:
            logger.error(f"获取图片向量失败: {e}")
            return None
    
    async def get_image_vector_info(self, image_id: int) -> Dict[str, Any]:
        """获取图片向量信息"""
        try:
            response = self.client.get(
                index=self.image_index,
                id=f"image_{image_id}"
            )
            
            source = response["_source"]
            return {
                "dimension": len(source.get("image_vector", [])),
                "model": source.get("model_version", "1.0"),
                "version": source.get("model_version", "1.0"),
                "created_at": source.get("created_at"),
                "updated_at": source.get("updated_at")
            }
            
        except Exception as e:
            logger.error(f"获取图片向量信息失败: {e}")
            return {}
    
    async def delete_document_chunk(self, chunk_id: int) -> bool:
        """删除文档分块索引"""
        try:
            self.client.delete(
                index=self.document_index,
                id=f"chunk_{chunk_id}"
            )
            return True
        except Exception as e:
            logger.error(f"删除文档分块索引失败: {e}")
            return False
    
    async def delete_image(self, image_id: int) -> bool:
        """删除图片索引"""
        try:
            self.client.delete(
                index=self.image_index,
                id=f"image_{image_id}"
            )
            return True
        except Exception as e:
            logger.error(f"删除图片索引失败: {e}")
            return False

    def delete_by_document(self, document_id: int) -> None:
        """删除与文档相关的所有索引（文档分块与图片）。"""
        try:
            # 分块索引
            self.client.delete_by_query(
                index=self.document_index,
                body={"query": {"term": {"document_id": document_id}}},
                refresh=True,
            )
        except Exception as e:
            logger.warning(f"删除文档分块索引失败: {e}")
        try:
            # 图片索引
            self.client.delete_by_query(
                index=self.image_index,
                body={"query": {"term": {"document_id": document_id}}},
                refresh=True,
            )
        except Exception as e:
            logger.warning(f"删除图片索引失败: {e}")
