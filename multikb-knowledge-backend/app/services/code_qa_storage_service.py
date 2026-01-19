"""
代码问答存储服务
负责将问答记录保存到 MySQL 和 OpenSearch
"""

import os
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.services.opensearch_service import OpenSearchService
from app.services.vector_service import VectorService
from app.models.code_qa import CodeQASession, CodeQARecord
from app.config.settings import settings

# OpenSearch 索引名称
CODE_QA_RECORDS_INDEX = "code_qa_records"


class CodeQAStorageService:
    """代码问答存储服务"""
    
    def __init__(self, db: Session):
        """
        初始化存储服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.opensearch_service = OpenSearchService()
        self.vector_service = VectorService(db)
    
    async def save_qa_to_opensearch(
        self,
        record_id: str,
        session_id: str,
        repository_id: int,
        question: str,
        answer: str,
        sources: List[str],
        context_data: List[Dict] = None,
        code_snippets: List[Dict] = None,
        mermaid_diagrams: str = None,
        question_type: str = None,
        classification: Dict = None,
        call_chain_info: Dict = None,
        processing_info: Dict = None
    ) -> str:
        """
        保存问答记录到 OpenSearch
        
        Args:
            record_id: 记录ID
            session_id: 会话ID
            repository_id: 仓库ID
            question: 问题文本
            answer: 答案文本
            sources: 来源文件路径列表
            context_data: 上下文文件详细信息
            code_snippets: 代码片段列表
            mermaid_diagrams: Mermaid 流程图代码
            question_type: 问题类型
            classification: 分类信息
            call_chain_info: 调用链信息
            processing_info: 处理信息
            
        Returns:
            OpenSearch 文档ID
        """
        try:
            # 生成向量
            question_vector = self.vector_service.generate_embedding(question)
            answer_vector = self.vector_service.generate_embedding(answer)
            
            # 构建上下文文件信息
            context_files_info = []
            if context_data:
                for ctx in context_data:
                    context_files_info.append({
                        "file_path": ctx.get('path', ''),
                        "file_name": os.path.basename(ctx.get('path', '')),
                        "language": ctx.get('language', ''),
                        "content_summary": ctx.get('content', '')[:500]  # 只存储摘要
                    })
            
            # 构建文档
            doc = {
                "record_id": record_id,
                "session_id": session_id,
                "repository_id": repository_id,
                "question": question,
                "answer": answer,
                "question_vector": question_vector,
                "answer_vector": answer_vector,
                "context_files": context_files_info,
                "code_snippets": code_snippets or [],
                "mermaid_diagrams": mermaid_diagrams,
                "question_type": question_type,
                "classification": classification,
                "call_chain_info": call_chain_info,
                "processing_info": processing_info,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 保存到 OpenSearch（使用 record_id 作为文档ID）
            self.opensearch_service.client.index(
                index=CODE_QA_RECORDS_INDEX,
                id=record_id,
                body=doc
            )
            
            logger.info(f"保存问答记录到 OpenSearch 成功: record_id={record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"保存问答记录到 OpenSearch 失败: {e}", exc_info=True)
            raise
    
    async def save_qa_to_mysql(
        self,
        record_id: str,
        session_id: str,
        repository_id: int,
        question: str,
        answer: str,
        opensearch_doc_id: str,
        sources: List[str],
        question_type: str = None,
        processing_time: float = None,
        token_usage: int = None,
        has_mermaid: bool = False,
        has_code_snippets: bool = False
    ):
        """
        保存问答记录到 MySQL
        
        Args:
            record_id: 记录ID
            session_id: 会话ID
            repository_id: 仓库ID
            question: 问题文本
            answer: 答案文本
            opensearch_doc_id: OpenSearch 文档ID
            sources: 来源文件路径列表
            question_type: 问题类型
            processing_time: 处理时间（秒）
            token_usage: Token使用量
            has_mermaid: 是否包含流程图
            has_code_snippets: 是否包含代码片段
        """
        try:
            # 1. 获取或创建会话
            session = self.db.query(CodeQASession).filter(
                CodeQASession.session_id == session_id
            ).first()
            
            if not session:
                session = CodeQASession(
                    session_id=session_id,
                    session_name=f"代码问答 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    repository_id=repository_id,
                    question_count=0,
                    status='active'
                )
                self.db.add(session)
                self.db.flush()
            
            # 2. 创建问答记录
            record = CodeQARecord(
                record_id=record_id,
                session_id=session_id,
                repository_id=repository_id,
                question_summary=question[:500],
                answer_summary=answer[:500],
                opensearch_doc_id=opensearch_doc_id,
                source_count=len(sources),
                sources=json.dumps(sources, ensure_ascii=False) if sources else None,
                question_type=question_type,
                processing_time=processing_time,
                token_usage=token_usage,
                has_mermaid=has_mermaid,
                has_code_snippets=has_code_snippets
            )
            self.db.add(record)
            
            # 3. 更新会话统计
            session.question_count += 1
            session.last_question = question[:500]
            session.last_answer_summary = answer[:500]
            session.last_activity_time = datetime.now()
            
            self.db.commit()
            logger.info(f"保存问答记录到 MySQL 成功: record_id={record_id}, session_id={session_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存问答记录到 MySQL 失败: {e}", exc_info=True)
            raise
    
    def get_qa_sessions(
        self,
        repository_id: int,
        user_id: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        查询问答会话列表
        
        Args:
            repository_id: 仓库ID
            user_id: 用户ID（可选）
            page: 页码
            page_size: 每页数量
            
        Returns:
            会话列表
        """
        query = self.db.query(CodeQASession).filter(
            CodeQASession.repository_id == repository_id,
            CodeQASession.is_deleted == False
        )
        
        if user_id:
            query = query.filter(CodeQASession.user_id == user_id)
        
        total = query.count()
        sessions = query.order_by(
            CodeQASession.last_activity_time.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total": total,
            "items": [{
                "session_id": s.session_id,
                "session_name": s.session_name,
                "question_count": s.question_count,
                "last_question": s.last_question,
                "last_activity_time": s.last_activity_time.isoformat() if s.last_activity_time else None,
                "created_at": s.created_at.isoformat() if s.created_at else None
            } for s in sessions]
        }
    
    def get_qa_records(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 50
    ) -> Dict:
        """
        查询会话中的问答记录列表（仅元数据）
        
        Args:
            session_id: 会话ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            记录列表
        """
        query = self.db.query(CodeQARecord).filter(
            CodeQARecord.session_id == session_id,
            CodeQARecord.is_deleted == False
        )
        
        total = query.count()
        records = query.order_by(
            CodeQARecord.created_at.asc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total": total,
            "items": [{
                "record_id": r.record_id,
                "question_summary": r.question_summary,
                "answer_summary": r.answer_summary,
                "source_count": r.source_count,
                "sources": json.loads(r.sources) if r.sources else [],
                "has_mermaid": r.has_mermaid,
                "has_code_snippets": r.has_code_snippets,
                "created_at": r.created_at.isoformat() if r.created_at else None
            } for r in records]
        }
    
    def get_qa_record_detail(self, record_id: str) -> Optional[Dict]:
        """
        查询完整的问答记录（从 OpenSearch）
        
        Args:
            record_id: 记录ID
            
        Returns:
            完整记录详情，如果不存在则返回 None
        """
        try:
            result = self.opensearch_service.client.get(
                index=CODE_QA_RECORDS_INDEX,
                id=record_id
            )
            
            return result["_source"]
        except Exception as e:
            logger.error(f"查询 OpenSearch 记录失败: {e}")
            return None
    
    def search_qa_records(
        self,
        repository_id: int,
        query: str,
        search_mode: str = "hybrid",  # vector/keyword/hybrid
        top_k: int = 10
    ) -> List[Dict]:
        """
        搜索问答记录（支持向量搜索、关键词搜索、混合搜索）
        
        Args:
            repository_id: 仓库ID
            query: 搜索查询
            search_mode: 搜索模式（vector/keyword/hybrid）
            top_k: 返回数量
            
        Returns:
            匹配的记录列表
        """
        try:
            # 生成查询向量
            query_vector = self.vector_service.generate_embedding(query)
            
            if search_mode == "vector":
                # 纯向量搜索
                body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"repository_id": repository_id}}
                            ],
                            "should": [
                                {
                                    "knn": {
                                        "question_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                },
                                {
                                    "knn": {
                                        "answer_vector": {
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
                body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"repository_id": repository_id}},
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["question^2", "answer"],
                                        "type": "best_fields"
                                    }
                                }
                            ]
                        }
                    }
                }
            else:
                # 混合搜索
                body = {
                    "size": top_k,
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"repository_id": repository_id}}
                            ],
                            "should": [
                                {
                                    "knn": {
                                        "question_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                },
                                {
                                    "knn": {
                                        "answer_vector": {
                                            "vector": query_vector,
                                            "k": top_k
                                        }
                                    }
                                },
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["question^2", "answer"],
                                        "type": "best_fields"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                }
            
            results = self.opensearch_service.client.search(
                index=CODE_QA_RECORDS_INDEX,
                body=body
            )
            
            return [hit["_source"] for hit in results["hits"]["hits"]]
            
        except Exception as e:
            logger.error(f"搜索问答记录失败: {e}", exc_info=True)
            return []
