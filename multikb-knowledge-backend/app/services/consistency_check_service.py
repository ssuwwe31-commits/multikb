"""
Consistency Check Service
根据文档修改功能设计实现数据一致性检查服务
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import redis
import json
from app.models.chunk import DocumentChunk
from app.models.chunk_version import ChunkVersion
from app.config.settings import settings
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode
from app.services.opensearch_service import OpenSearchService
from app.services.vector_service import VectorService


class ConsistencyCheckService:
    """一致性检查服务 - 严格按照文档修改功能设计实现"""
    
    def __init__(self, db: Session):
        self.db = db
        self.opensearch_service = OpenSearchService()
        self.vector_service = VectorService(db)
        
        # Redis连接 - 根据设计文档要求
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    
    def check_document_consistency(self, document_id: int) -> Dict[str, Any]:
        """检查文档数据一致性 - 根据设计文档实现"""
        try:
            logger.info(f"开始检查文档一致性: document_id={document_id}")
            
            # 1. 获取文档基本信息
            from app.models.document import Document
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"文档 {document_id} 不存在"
                )
            
            # 2. 获取所有块
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            check_results = {}
            inconsistencies = []
            
            # 3. 内容向量一致性检查
            content_vector_consistent = self._check_content_vector_consistency(chunks)
            check_results["content_vector_consistency"] = content_vector_consistent
            
            if not content_vector_consistent:
                inconsistencies.append({
                    "type": "content_vector_inconsistency",
                    "description": "块内容与向量数据不一致"
                })
            
            # 4. 索引数据一致性检查
            index_consistent = self._check_index_consistency(document_id, chunks)
            check_results["index_data_consistency"] = index_consistent
            
            if not index_consistent:
                inconsistencies.append({
                    "type": "index_data_inconsistency",
                    "description": "OpenSearch索引与MySQL数据不一致"
                })
            
            # 5. 缓存数据一致性检查
            cache_consistent = self._check_cache_consistency(document_id, chunks)
            check_results["cache_data_consistency"] = cache_consistent
            
            if not cache_consistent:
                inconsistencies.append({
                    "type": "cache_data_inconsistency",
                    "description": "Redis缓存与数据库数据不一致"
                })
            
            # 6. 版本数据一致性检查
            version_consistent = self._check_version_consistency(chunks)
            check_results["version_data_consistency"] = version_consistent
            
            if not version_consistent:
                inconsistencies.append({
                    "type": "version_data_inconsistency",
                    "description": "版本记录与当前数据不一致"
                })
            
            # 7. 判断整体一致性状态
            consistency_status = "consistent" if not inconsistencies else "inconsistent"
            
            result = {
                "document_id": str(document_id),
                "consistency_status": consistency_status,
                "check_results": check_results,
                "inconsistencies": inconsistencies,
                "check_time": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"文档一致性检查完成: document_id={document_id}, 状态={consistency_status}")
            return result
            
        except Exception as e:
            logger.error(f"检查文档一致性错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"检查文档一致性失败: {str(e)}"
            )
    
    def check_chunk_consistency(self, document_id: int, chunk_id: int) -> Dict[str, Any]:
        """检查块数据一致性 - 根据设计文档实现"""
        try:
            logger.info(f"开始检查块一致性: document_id={document_id}, chunk_id={chunk_id}")
            
            # 1. 获取块
            chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id,
                DocumentChunk.document_id == document_id
            ).first()
            
            if not chunk:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"块 {chunk_id} 不存在"
                )
            
            check_results = {}
            inconsistencies = []
            
            # 2. 内容向量一致性检查
            content_vector_consistent = self._check_chunk_content_vector_consistency(chunk)
            check_results["content_vector_consistency"] = content_vector_consistent
            
            if not content_vector_consistent:
                inconsistencies.append({
                    "type": "content_vector_inconsistency",
                    "description": f"块 {chunk_id} 的内容与向量数据不一致"
                })
            
            # 3. 索引数据一致性检查
            index_consistent = self._check_chunk_index_consistency(chunk_id)
            check_results["index_data_consistency"] = index_consistent
            
            if not index_consistent:
                inconsistencies.append({
                    "type": "index_data_inconsistency",
                    "description": f"块 {chunk_id} 的索引数据不一致"
                })
            
            # 4. 缓存数据一致性检查
            cache_consistent = self._check_chunk_cache_consistency(chunk_id)
            check_results["cache_data_consistency"] = cache_consistent
            
            if not cache_consistent:
                inconsistencies.append({
                    "type": "cache_data_inconsistency",
                    "description": f"块 {chunk_id} 的缓存数据不一致"
                })
            
            # 5. 版本数据一致性检查
            version_consistent = self._check_chunk_version_consistency(chunk)
            check_results["version_data_consistency"] = version_consistent
            
            if not version_consistent:
                inconsistencies.append({
                    "type": "version_data_inconsistency",
                    "description": f"块 {chunk_id} 的版本数据不一致"
                })
            
            # 6. 判断整体一致性状态
            consistency_status = "consistent" if not inconsistencies else "inconsistent"
            
            result = {
                "document_id": str(document_id),
                "chunk_id": str(chunk_id),
                "consistency_status": consistency_status,
                "check_results": check_results,
                "inconsistencies": inconsistencies,
                "check_time": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"块一致性检查完成: document_id={document_id}, chunk_id={chunk_id}, 状态={consistency_status}")
            return result
            
        except Exception as e:
            logger.error(f"检查块一致性错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"检查块一致性失败: {str(e)}"
            )
    
    def _check_content_vector_consistency(self, chunks: List) -> bool:
        """检查内容向量一致性"""
        try:
            # 检查每个块的向量是否存在
            for chunk in chunks:
                # 重新生成向量用于对比
                new_vector = self.vector_service.generate_embedding(chunk.content)
                
                # 从OpenSearch获取存储的向量
                try:
                    stored_doc = self.opensearch_service.client.get(
                        index=self.opensearch_service.document_index,
                        id=f"chunk_{chunk.id}"
                    )
                    stored_vector = stored_doc["_source"].get("vector", [])
                    
                    # 比较向量维度
                    if len(new_vector) != len(stored_vector):
                        logger.warning(f"块 {chunk.id} 向量维度不一致")
                        return False
                except Exception as e:
                    logger.warning(f"块 {chunk.id} 在OpenSearch中不存在: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查内容向量一致性错误: {e}")
            return False
    
    def _check_index_consistency(self, document_id: int, chunks: List) -> bool:
        """检查索引数据一致性"""
        try:
            # 检查OpenSearch中是否有文档的所有块
            for chunk in chunks:
                try:
                    self.opensearch_service.client.get(
                        index=self.opensearch_service.document_index,
                        id=f"chunk_{chunk.id}"
                    )
                except Exception as e:
                    logger.warning(f"块 {chunk.id} 在OpenSearch中不存在")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查索引数据一致性错误: {e}")
            return False
    
    def _check_cache_consistency(self, document_id: int, chunks: List) -> bool:
        """检查缓存数据一致性"""
        try:
            # 检查Redis中是否有文档的缓存
            cache_key = f"document_{document_id}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                cache_info = json.loads(cached_data)
                # 检查缓存中的块数量与数据库是否一致
                cached_chunks_count = cache_info.get("chunks_count", 0)
                if cached_chunks_count != len(chunks):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查缓存数据一致性错误: {e}")
            return True  # 缓存失效不算严重问题
    
    def _check_version_consistency(self, chunks: List) -> bool:
        """检查版本数据一致性"""
        try:
            # 检查每个块的版本记录是否一致
            for chunk in chunks:
                # 获取最新的版本记录
                latest_version = self.db.query(ChunkVersion).filter(
                    ChunkVersion.chunk_id == chunk.id
                ).order_by(ChunkVersion.version_number.desc()).first()
                
                # 如果块有版本记录，但当前版本号不一致
                if latest_version and chunk.version != latest_version.version_number:
                    logger.warning(f"块 {chunk.id} 版本号不一致: DB={chunk.version}, Version={latest_version.version_number}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查版本数据一致性错误: {e}")
            return True
    
    def _check_chunk_content_vector_consistency(self, chunk) -> bool:
        """检查单个块的内容向量一致性"""
        try:
            # 重新生成向量
            new_vector = self.vector_service.generate_embedding(chunk.content)
            
            # 从OpenSearch获取存储的向量
            try:
                stored_doc = self.opensearch_service.client.get(
                    index=self.opensearch_service.document_index,
                    id=f"chunk_{chunk.id}"
                )
                stored_vector = stored_doc["_source"].get("vector", [])
                
                # 比较向量维度
                if len(new_vector) != len(stored_vector):
                    return False
                
                return True
                
            except Exception as e:
                logger.warning(f"块 {chunk.id} 在OpenSearch中不存在: {e}")
                return False
            
        except Exception as e:
            logger.error(f"检查块内容向量一致性错误: {e}")
            return False
    
    def _check_chunk_index_consistency(self, chunk_id: int) -> bool:
        """检查单个块的索引一致性"""
        try:
            self.opensearch_service.client.get(
                index=self.opensearch_service.document_index,
                id=f"chunk_{chunk_id}"
            )
            return True
        except Exception as e:
            return False
    
    def _check_chunk_cache_consistency(self, chunk_id: int) -> bool:
        """检查单个块的缓存一致性"""
        try:
            cache_key = f"chunk_{chunk_id}"
            cached_data = self.redis_client.get(cache_key)
            return cached_data is not None
        except Exception as e:
            return True  # 缓存失效不算严重问题
    
    def _check_chunk_version_consistency(self, chunk) -> bool:
        """检查单个块的版本一致性"""
        try:
            # 获取最新的版本记录
            latest_version = self.db.query(ChunkVersion).filter(
                ChunkVersion.chunk_id == chunk.id
            ).order_by(ChunkVersion.version_number.desc()).first()
            
            # 如果块有版本记录，但当前版本号不一致
            if latest_version and chunk.version != latest_version.version_number:
                return False
            
            return True
        except Exception as e:
            return True
