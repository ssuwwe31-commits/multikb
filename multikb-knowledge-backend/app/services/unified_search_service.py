"""
Unified Search Service
统一搜索服务 - 同时搜索文档和代码
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import asyncio

from app.core.logging import logger
from app.services.opensearch_service import OpenSearchService
from app.services.vector_service import VectorService
from opensearch_schemas.code_indices import CODE_FILES_INDEX, CODE_SYMBOLS_INDEX
from app.config.settings import settings


class UnifiedSearchService:
    """统一搜索服务 - 支持文档+代码的混合搜索"""
    
    def __init__(self, db: Session):
        self.db = db
        self.opensearch = OpenSearchService()
        # 复用知识库的向量化服务（需要传入 db）
        self.vector_service = VectorService(db)
        # 复用知识库的 rerank 服务
        from app.services.rerank_service import RerankService
        self.rerank_service = RerankService()
    
    async def search(
        self,
        query: str,
        knowledge_base_id: Optional[int] = None,
        search_scope: List[str] = ["documents", "code"],
        search_mode: str = "hybrid",  # hybrid/vector/keyword
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        统一搜索（文档 + 代码）
        
        Args:
            query: 搜索查询
            knowledge_base_id: 知识库ID筛选
            search_scope: 搜索范围 ["documents", "code"] 或其子集
            search_mode: 搜索模式
            top_k: 返回结果数量
            filters: 额外筛选条件
            
        Returns:
            搜索结果（按相关度排序，文档和代码混合）
        """
        try:
            results = []
            
            # 1. 搜索文档
            if "documents" in search_scope:
                doc_results = await self._search_documents(
                    query=query,
                    knowledge_base_id=knowledge_base_id,
                    search_mode=search_mode,
                    top_k=top_k,
                    filters=filters
                )
                results.extend(doc_results)
            
            # 2. 搜索代码
            if "code" in search_scope:
                code_results = await self._search_code(
                    query=query,
                    knowledge_base_id=knowledge_base_id,
                    search_mode=search_mode,
                    top_k=top_k,
                    filters=filters
                )
                results.extend(code_results)
            
            # 3. 融合和排序结果（使用 rerank 优化）
            results = self._merge_and_rank_results(results, top_k, query=query)
            
            return {
                "query": query,
                "total": len(results),
                "results": results,
                "search_mode": search_mode,
                "search_scope": search_scope
            }
            
        except Exception as e:
            logger.error(f"统一搜索失败: {e}")
            raise
    
    async def _search_documents(
        self,
        query: str,
        knowledge_base_id: Optional[int] = None,
        search_mode: str = "hybrid",
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索文档"""
        try:
            # 构建查询
            must_clauses = []
            
            if knowledge_base_id:
                must_clauses.append({
                    "term": {"knowledge_base_id": knowledge_base_id}
                })
            
            if filters:
                for key, value in filters.items():
                    must_clauses.append({
                        "term": {key: value}
                    })
            
            # 根据搜索模式构建查询
            if search_mode == "vector":
                # 纯向量搜索（同步方法，需要在异步上下文中在线程池执行）
                query_vector = await asyncio.to_thread(
                    self.vector_service.generate_embedding,
                    query
                )
                
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            
            elif search_mode == "keyword":
                # 纯关键词搜索
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses + [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["content", "title"],
                                        "type": "best_fields"
                                    }
                                }
                            ]
                        }
                    }
                }
            
            else:
                # 混合搜索（向量 + 关键词）（同步方法，需要在异步上下文中在线程池执行）
                query_vector = await asyncio.to_thread(
                    self.vector_service.generate_embedding,
                    query
                )
                
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                },
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["content^2", "title^3"],
                                        "type": "best_fields"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                }
            
            # 执行搜索（同步方法需要在异步上下文中在线程池执行）
            response = await asyncio.to_thread(
                self.opensearch.client.search,
                index=settings.DOCUMENT_INDEX_NAME,
                body=search_body
            )
            
            # 解析结果
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append({
                    "type": "document",
                    "id": source.get('document_id'),
                    "title": source.get('title', ''),
                    "content": source.get('content', '')[:200],  # 摘要
                    "knowledge_base_id": source.get('knowledge_base_id'),
                    "score": hit['_score'],
                    "highlight": hit.get('highlight', {})
                })
            
            return results
            
        except Exception as e:
            logger.error(f"搜索文档失败: {e}")
            return []
    
    async def _search_code(
        self,
        query: str,
        knowledge_base_id: Optional[int] = None,
        search_mode: str = "hybrid",
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索代码（文件 + 符号）"""
        try:
            results = []
            
            # 1. 搜索代码文件
            file_results = await self._search_code_files(
                query, knowledge_base_id, search_mode, top_k // 2, filters
            )
            results.extend(file_results)
            
            # 2. 搜索代码符号
            symbol_results = await self._search_code_symbols(
                query, knowledge_base_id, search_mode, top_k // 2, filters
            )
            results.extend(symbol_results)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索代码失败: {e}")
            return []
    
    async def _search_code_files(
        self,
        query: str,
        knowledge_base_id: Optional[int],
        search_mode: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """搜索代码文件"""
        try:
            must_clauses = []
            
            if knowledge_base_id:
                must_clauses.append({
                    "term": {"knowledge_base_id": knowledge_base_id}
                })
            
            # 处理 filters 参数
            if filters:
                # 支持 repository_id 过滤
                if 'repository_id' in filters:
                    must_clauses.append({
                        "term": {"repository_id": filters['repository_id']}
                    })
                # 支持 language 过滤
                if 'language' in filters:
                    must_clauses.append({
                        "term": {"language": filters['language']}
                    })
                # 支持按目录路径前缀过滤（新增）
                if 'file_path_prefix' in filters or 'directory' in filters:
                    path_prefix = filters.get('file_path_prefix') or filters.get('directory')
                    if path_prefix:
                        # 确保路径以 / 结尾（用于前缀匹配）
                        if not path_prefix.endswith('/') and '/' in path_prefix:
                            path_prefix = path_prefix.rsplit('/', 1)[0] + '/'
                        must_clauses.append({
                            "prefix": {
                                "file_path.keyword": path_prefix
                            }
                        })
            
            # 生成查询向量（同步方法，需要在异步上下文中在线程池执行）
            if search_mode in ["vector", "hybrid"]:
                query_vector = await asyncio.to_thread(
                    self.vector_service.generate_embedding,
                    query
                )
            
            # 构建查询
            if search_mode == "vector":
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            elif search_mode == "keyword":
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses + [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["content^2", "file_path", "file_name^3"],
                                        "type": "best_fields"
                                    }
                                }
                            ]
                        }
                    }
                }
            else:  # hybrid
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                },
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["content^2", "file_path", "file_name^3"],
                                        "type": "best_fields"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                }
            
            # 执行搜索（同步方法需要在异步上下文中在线程池执行）
            response = await asyncio.to_thread(
                self.opensearch.client.search,
                index=CODE_FILES_INDEX,
                body=search_body
            )
            
            # 解析结果
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append({
                    "type": "code_file",
                    "id": source.get('file_id'),
                    "file_path": source.get('file_path'),
                    "file_name": source.get('file_name'),
                    "language": source.get('language'),
                    "content": source.get('content_summary', '')[:200],
                    "repository_id": source.get('repository_id'),
                    "knowledge_base_id": source.get('knowledge_base_id'),
                    "lines_of_code": source.get('lines_of_code'),
                    "complexity_score": source.get('complexity_score'),
                    "score": hit['_score']
                })
            
            return results
            
        except Exception as e:
            logger.error(f"搜索代码文件失败: {e}")
            return []
    
    async def _search_code_symbols(
        self,
        query: str,
        knowledge_base_id: Optional[int],
        search_mode: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """搜索代码符号"""
        try:
            must_clauses = []
            
            if knowledge_base_id:
                must_clauses.append({
                    "term": {"knowledge_base_id": knowledge_base_id}
                })
            
            # 生成查询向量（同步方法，需要在异步上下文中在线程池执行）
            if search_mode in ["vector", "hybrid"]:
                query_vector = await asyncio.to_thread(
                    self.vector_service.generate_embedding,
                    query
                )
            
            # 构建查询
            if search_mode == "vector":
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            elif search_mode == "keyword":
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses + [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": [
                                            "symbol_name^3",
                                            "qualified_name^2",
                                            "docstring",
                                            "signature",
                                            "code_content"
                                        ],
                                        "type": "best_fields"
                                    }
                                }
                            ]
                        }
                    }
                }
            else:  # hybrid
                search_body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": must_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                },
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": [
                                            "symbol_name^3",
                                            "qualified_name^2",
                                            "docstring",
                                            "signature",
                                            "code_content"
                                        ],
                                        "type": "best_fields"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                }
            
            # 执行搜索（同步方法需要在异步上下文中在线程池执行）
            response = await asyncio.to_thread(
                self.opensearch.client.search,
                index=CODE_SYMBOLS_INDEX,
                body=search_body
            )
            
            # 解析结果
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append({
                    "type": "code_symbol",
                    "id": source.get('symbol_id'),
                    "symbol_name": source.get('symbol_name'),
                    "symbol_type": source.get('symbol_type'),
                    "qualified_name": source.get('qualified_name'),
                    "signature": source.get('signature'),
                    "docstring": source.get('docstring', '')[:200],
                    "file_path": source.get('file_path'),
                    "repository_id": source.get('repository_id'),
                    "knowledge_base_id": source.get('knowledge_base_id'),
                    "complexity_score": source.get('complexity_score'),
                    "score": hit['_score']
                })
            
            return results
            
        except Exception as e:
            logger.error(f"搜索代码符号失败: {e}")
            return []
    
    def _merge_and_rank_results(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        融合和排序搜索结果（使用 Rerank 优化）
        
        Args:
            results: 所有搜索结果
            top_k: 返回数量
            query: 查询文本（用于 rerank，可选）
            
        Returns:
            排序后的结果
        """
        try:
            # 如果结果为空，直接返回
            if not results:
                return []
            
            # 如果提供了查询文本且 rerank 可用，使用 rerank 排序
            if query and self.rerank_service.is_available() and len(results) > 1:
                # 如果结果太多，先初步排序，保留更多候选供 rerank
                if len(results) > top_k * 3:
                    results.sort(key=lambda x: x.get('score', 0), reverse=True)
                    results = results[:top_k * 3]
                
                # 准备 rerank 候选（需要 content 字段）
                rerank_candidates = []
                for result in results:
                    content = self._extract_content_for_rerank(result)
                    rerank_candidates.append({
                        **result,
                        'content': content,
                        'score': result.get('score', 0.0)  # 保留原始分数
                    })
                
                # 使用 rerank 重新排序
                try:
                    reranked_results = self.rerank_service.rerank(
                        query=query,
                        candidates=rerank_candidates,
                        top_k=top_k
                    )
                    logger.info(f"代码搜索 Rerank 完成: 输入={len(rerank_candidates)}, 输出={len(reranked_results)}")
                    return reranked_results
                except Exception as rerank_error:
                    logger.warning(f"Rerank 排序失败，降级到简单排序: {rerank_error}")
                    # 降级：简单排序
                    results.sort(key=lambda x: x.get('score', 0), reverse=True)
                    return results[:top_k]
            else:
                # 没有查询文本或 rerank 不可用，使用简单排序
                sorted_results = sorted(
                    results,
                    key=lambda x: x.get('score', 0),
                    reverse=True
                )
                return sorted_results[:top_k]
            
        except Exception as e:
            logger.error(f"融合排序结果失败: {e}")
            # 降级：简单排序
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:top_k] if len(results) > top_k else results
    
    def _extract_content_for_rerank(self, result: Dict[str, Any]) -> str:
        """
        从搜索结果中提取用于 rerank 的文本内容
        
        Args:
            result: 搜索结果字典
            
        Returns:
            文本内容
        """
        # 根据结果类型提取内容
        result_type = result.get('type', '')
        
        if result_type == 'code_symbol':
            # 代码符号：符号名 + 签名 + 文档字符串
            parts = []
            if result.get('symbol_name'):
                parts.append(f"符号: {result['symbol_name']}")
            if result.get('qualified_name'):
                parts.append(f"完整名: {result['qualified_name']}")
            if result.get('signature'):
                parts.append(f"签名: {result['signature']}")
            if result.get('docstring'):
                docstring = result['docstring'][:500] if len(result.get('docstring', '')) > 500 else result.get('docstring', '')
                parts.append(f"说明: {docstring}")
            return '\n\n'.join(parts) if parts else result.get('symbol_name', '')
        
        elif result_type == 'code_file':
            # 代码文件：文件路径 + 内容摘要
            parts = []
            if result.get('file_path'):
                parts.append(f"文件: {result['file_path']}")
            if result.get('content_summary'):
                parts.append(f"内容: {result['content_summary']}")
            return '\n\n'.join(parts) if parts else result.get('file_path', '')
        
        else:
            # 其他类型：尝试提取 content 字段
            return result.get('content', '') or result.get('docstring', '') or str(result)
    
    async def search_by_vector(
        self,
        vector: List[float],
        search_scope: List[str] = ["documents", "code"],
        knowledge_base_id: Optional[int] = None,
        top_k: int = 20
    ) -> Dict[str, Any]:
        """
        使用向量搜索
        
        Args:
            vector: 查询向量
            search_scope: 搜索范围
            knowledge_base_id: 知识库ID筛选
            top_k: 返回数量
            
        Returns:
            搜索结果
        """
        try:
            results = []
            
            # 构建过滤条件
            filter_clauses = []
            if knowledge_base_id:
                filter_clauses.append({
                    "term": {"knowledge_base_id": knowledge_base_id}
                })
            
            # 1. 搜索文档向量
            if "documents" in search_scope:
                doc_body = {
                    "size": top_k // 2,
                    "query": {
                        "bool": {
                            "must": filter_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": vector,
                                            "k": top_k // 2
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
                
                doc_response = await asyncio.to_thread(
                    self.opensearch.client.search,
                    index=settings.DOCUMENT_INDEX_NAME,
                    body=doc_body
                )
                
                for hit in doc_response['hits']['hits']:
                    source = hit['_source']
                    results.append({
                        "type": "document",
                        "id": source.get('document_id'),
                        "title": source.get('title', ''),
                        "content": source.get('content', '')[:200],
                        "score": hit['_score']
                    })
            
            # 2. 搜索代码文件向量
            if "code" in search_scope:
                file_body = {
                    "size": top_k // 4,
                    "query": {
                        "bool": {
                            "must": filter_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": vector,
                                            "k": top_k // 4
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
                
                file_response = await asyncio.to_thread(
                    self.opensearch.client.search,
                    index=CODE_FILES_INDEX,
                    body=file_body
                )
                
                for hit in file_response['hits']['hits']:
                    source = hit['_source']
                    results.append({
                        "type": "code_file",
                        "id": source.get('file_id'),
                        "file_path": source.get('file_path'),
                        "language": source.get('language'),
                        "score": hit['_score']
                    })
                
                # 3. 搜索代码符号向量
                symbol_body = {
                    "size": top_k // 4,
                    "query": {
                        "bool": {
                            "must": filter_clauses,
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": vector,
                                            "k": top_k // 4
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
                
                symbol_response = await asyncio.to_thread(
                    self.opensearch.client.search,
                    index=CODE_SYMBOLS_INDEX,
                    body=symbol_body
                )
                
                for hit in symbol_response['hits']['hits']:
                    source = hit['_source']
                    results.append({
                        "type": "code_symbol",
                        "id": source.get('symbol_id'),
                        "symbol_name": source.get('symbol_name'),
                        "symbol_type": source.get('symbol_type'),
                        "docstring": source.get('docstring', '')[:200],
                        "score": hit['_score']
                    })
            
            # 融合排序（向量搜索没有查询文本，不使用 rerank）
            results = self._merge_and_rank_results(results, top_k, query=None)
            
            return {
                "total": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return {"total": 0, "results": []}


# ============================================
# 便捷函数
# ============================================

def get_unified_search_service(db: Session) -> UnifiedSearchService:
    """获取统一搜索服务实例"""
    return UnifiedSearchService(db)
