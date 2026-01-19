"""
Unified QA Service
统一问答服务 - 支持文档+代码的上下文问答
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import requests
import asyncio

from app.core.logging import logger
from app.services.unified_search_service import get_unified_search_service
from app.services.opensearch_service import OpenSearchService
from app.services.vector_service import VectorService
from app.config.settings import settings


class UnifiedQAService:
    """统一问答服务 - 跨文档和代码的智能问答"""
    
    def __init__(self, db: Session):
        self.db = db
        self.search_service = get_unified_search_service(db)
        self.opensearch = OpenSearchService()
        # 复用知识库的向量化服务（需要传入 db）
        self.vector_service = VectorService(db)
    
    async def answer_question(
        self,
        question: str,
        knowledge_base_id: Optional[int] = None,
        search_scope: List[str] = ["documents", "code"],
        max_context_items: int = 5,
        include_code_context: bool = True
    ) -> Dict[str, Any]:
        """
        回答问题（基于文档+代码上下文）
        
        Args:
            question: 用户问题
            knowledge_base_id: 知识库ID筛选
            search_scope: 搜索范围
            max_context_items: 最大上下文项数
            include_code_context: 是否包含代码上下文
            
        Returns:
            问答结果（答案 + 来源）
        """
        try:
            # 1. 检索相关内容（文档 + 代码）
            search_results = await self.search_service.search(
                query=question,
                knowledge_base_id=knowledge_base_id,
                search_scope=search_scope,
                search_mode="hybrid",
                top_k=max_context_items * 2  # 多检索一些，后续精选
            )
            
            # 2. 构建上下文
            context = self._build_context(
                search_results['results'][:max_context_items],
                include_code_context=include_code_context
            )
            
            # 3. 调用 LLM 生成答案
            answer = await self._generate_answer(question, context)
            
            # 4. 组装来源信息
            sources = self._extract_sources(search_results['results'][:max_context_items])
            
            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "context_items": len(context['items']),
                "search_scope": search_scope,
                "knowledge_base_id": knowledge_base_id
            }
            
        except Exception as e:
            logger.error(f"统一问答失败: {e}")
            raise
    
    def _build_context(
        self,
        search_results: List[Dict[str, Any]],
        include_code_context: bool = True
    ) -> Dict[str, Any]:
        """
        构建上下文（文档 + 代码）
        
        Args:
            search_results: 搜索结果列表
            include_code_context: 是否包含代码上下文
            
        Returns:
            上下文数据
        """
        try:
            context_items = []
            
            for result in search_results:
                result_type = result.get('type')
                
                if result_type == 'document':
                    # 文档上下文
                    context_items.append({
                        "type": "document",
                        "source": f"文档: {result.get('title', 'Unknown')}",
                        "content": result.get('content', ''),
                        "score": result.get('score', 0)
                    })
                
                elif result_type == 'code_file' and include_code_context:
                    # 代码文件上下文
                    context_items.append({
                        "type": "code_file",
                        "source": f"代码文件: {result.get('file_path', 'Unknown')}",
                        "content": result.get('content', ''),
                        "language": result.get('language'),
                        "score": result.get('score', 0)
                    })
                
                elif result_type == 'code_symbol' and include_code_context:
                    # 代码符号上下文
                    symbol_content = f"{result.get('qualified_name', result.get('symbol_name'))}\n"
                    if result.get('signature'):
                        symbol_content += f"签名: {result.get('signature')}\n"
                    if result.get('docstring'):
                        symbol_content += f"文档: {result.get('docstring')}\n"
                    
                    context_items.append({
                        "type": "code_symbol",
                        "source": f"代码符号: {result.get('qualified_name', result.get('symbol_name'))} ({result.get('symbol_type')})",
                        "content": symbol_content,
                        "score": result.get('score', 0)
                    })
            
            return {
                "items": context_items,
                "total": len(context_items)
            }
            
        except Exception as e:
            logger.error(f"构建上下文失败: {e}")
            return {"items": [], "total": 0}
    
    async def _generate_answer(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> str:
        """
        生成答案（调用 LLM）
        
        Args:
            question: 用户问题
            context: 上下文数据
            
        Returns:
            答案文本
        """
        try:
            # 构建 Prompt
            context_text = ""
            for i, item in enumerate(context['items'], 1):
                context_text += f"\n[上下文 {i}] {item['source']}\n"
                context_text += f"{item['content']}\n"
                context_text += "-" * 60 + "\n"
            
            prompt = f"""你是一个专业的技术问答助手。请根据以下上下文（包括文档和代码）回答用户的问题。

上下文信息：
{context_text}

用户问题：
{question}

请提供详细、准确的答案。如果上下文中包含代码，可以引用代码片段来支持你的回答。如果无法从上下文中找到答案，请明确说明。

答案："""
            
            # 调用 Ollama API
            ollama_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL or settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 1000
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip()
                logger.info(f"生成答案成功，长度: {len(answer)}")
                return answer
            else:
                logger.error(f"LLM 调用失败: {response.status_code}")
                return "抱歉，生成答案时出现错误。"
            
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return "抱歉，生成答案时出现错误。"
    
    def _extract_sources(
        self,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        提取来源信息
        
        Args:
            search_results: 搜索结果列表
            
        Returns:
            来源列表
        """
        try:
            sources = []
            
            for result in search_results:
                result_type = result.get('type')
                
                if result_type == 'document':
                    sources.append({
                        "type": "document",
                        "id": result.get('id'),
                        "title": result.get('title', ''),
                        "score": result.get('score', 0)
                    })
                
                elif result_type == 'code_file':
                    sources.append({
                        "type": "code_file",
                        "id": result.get('id'),
                        "file_path": result.get('file_path', ''),
                        "language": result.get('language', ''),
                        "score": result.get('score', 0)
                    })
                
                elif result_type == 'code_symbol':
                    sources.append({
                        "type": "code_symbol",
                        "id": result.get('id'),
                        "symbol_name": result.get('qualified_name', result.get('symbol_name')),
                        "symbol_type": result.get('symbol_type', ''),
                        "file_path": result.get('file_path', ''),
                        "score": result.get('score', 0)
                    })
            
            return sources
            
        except Exception as e:
            logger.error(f"提取来源失败: {e}")
            return []
    
    async def get_code_examples(
        self,
        concept: str,
        knowledge_base_id: Optional[int] = None,
        language: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取代码示例（根据概念）
        
        Args:
            concept: 概念/关键词
            knowledge_base_id: 知识库ID筛选
            language: 编程语言筛选
            limit: 返回数量
            
        Returns:
            代码示例列表
        """
        try:
            # 使用向量搜索查找相关代码符号（同步方法，需要在异步上下文中在线程池执行）
            query_vector = await asyncio.to_thread(
                self.vector_service.generate_embedding,
                concept
            )
            
            # 构建查询
            must_clauses = []
            if knowledge_base_id:
                must_clauses.append({"term": {"knowledge_base_id": knowledge_base_id}})
            if language:
                must_clauses.append({"term": {"language": language}})
            
            search_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "should": [
                            {
                                "knn": {
                                    "content_vector": {
                                        "vector": query_vector,
                                        "k": limit
                                    }
                                }
                            }
                        ]
                    }
                }
            }
            
            from opensearch_schemas.code_indices import CODE_SYMBOLS_INDEX
            response = await asyncio.to_thread(
                self.opensearch.client.search,
                index=CODE_SYMBOLS_INDEX,
                body=search_body
            )
            
            # 解析结果
            examples = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                examples.append({
                    "symbol_id": source.get('symbol_id'),
                    "symbol_name": source.get('symbol_name'),
                    "symbol_type": source.get('symbol_type'),
                    "signature": source.get('signature'),
                    "docstring": source.get('docstring'),
                    "code_content": source.get('code_content'),
                    "file_path": source.get('file_path'),
                    "score": hit['_score']
                })
            
            logger.info(f"获取代码示例成功: {len(examples)} 个")
            return examples
            
        except Exception as e:
            logger.error(f"获取代码示例失败: {e}")
            return []


# ============================================
# 便捷函数
# ============================================

def get_unified_qa_service(db: Session) -> UnifiedQAService:
    """获取统一问答服务实例"""
    return UnifiedQAService(db)
