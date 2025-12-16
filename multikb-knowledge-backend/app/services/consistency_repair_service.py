"""
Consistency Repair Service
根据文档修改功能设计实现数据一致性修复服务
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import redis
import json
from app.models.chunk import DocumentChunk
from app.config.settings import settings
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode
from app.services.opensearch_service import OpenSearchService
from app.services.vector_service import VectorService


class ConsistencyRepairService:
    """一致性修复服务 - 严格按照文档修改功能设计实现"""
    
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
    
    def repair_document_consistency(self, document_id: int) -> Dict[str, Any]:
        """修复文档数据不一致问题 - 根据设计文档实现"""
        try:
            logger.info(f"开始修复文档一致性: document_id={document_id}")
            
            # 1. 获取文档和所有块
            from app.models.document import Document
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"文档 {document_id} 不存在"
                )
            
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            repair_results = {
                "vectors_rebuilt": 0,
                "indices_updated": 0,
                "cache_cleared": False,
                "versions_synced": False
            }
            
            # 2. 重新生成向量
            vectors_rebuilt = self._rebuild_vectors(chunks)
            repair_results["vectors_rebuilt"] = vectors_rebuilt
            
            # 3. 重新建立索引
            indices_updated = self._rebuild_indices(chunks)
            repair_results["indices_updated"] = indices_updated
            
            # 4. 同步缓存
            cache_cleared = self._sync_cache(document_id, chunks)
            repair_results["cache_cleared"] = cache_cleared
            
            # 5. 同步版本信息
            versions_synced = self._sync_versions(chunks)
            repair_results["versions_synced"] = versions_synced
            
            result = {
                "document_id": document_id,
                "repair_status": "completed",
                "repair_results": repair_results,
                "repair_time": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"文档一致性修复完成: document_id={document_id}")
            return result
            
        except Exception as e:
            logger.error(f"修复文档一致性错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"修复文档一致性失败: {str(e)}"
            )
    
    def _rebuild_vectors(self, chunks: List) -> int:
        """重新生成向量"""
        try:
            count = 0
            for chunk in chunks:
                # 重新生成向量
                new_vector = self.vector_service.generate_embedding(chunk.content)
                
                # 构建索引文档
                chunk_doc = {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "knowledge_base_id": getattr(chunk, 'knowledge_base_id', None),
                    "category_id": getattr(chunk, 'category_id', None),
                    "content": chunk.content,
                    "chunk_type": getattr(chunk, 'chunk_type', 'text'),
                    "metadata": getattr(chunk, 'metadata', {}),
                    "vector": new_vector,
                    "version": getattr(chunk, 'version', 1),
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None
                }
                
                # 更新OpenSearch索引
                self.opensearch_service.index_document_chunk(chunk_doc)
                count += 1
                
                logger.debug(f"重新生成向量: chunk_id={chunk.id}")
            
            return count
            
        except Exception as e:
            logger.error(f"重新生成向量错误: {e}")
            return 0
    
    def _rebuild_indices(self, chunks: List) -> int:
        """重新建立索引"""
        try:
            # OpenSearch索引已在_rebuild_vectors中更新
            # 这里主要是确认索引状态
            
            count = 0
            for chunk in chunks:
                try:
                    self.opensearch_service.client.get(
                        index=self.opensearch_service.document_index,
                        id=f"chunk_{chunk.id}"
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"块 {chunk.id} 索引更新失败: {e}")
            
            return count
            
        except Exception as e:
            logger.error(f"重新建立索引错误: {e}")
            return 0
    
    def _sync_cache(self, document_id: int, chunks: List) -> bool:
        """同步缓存"""
        try:
            # 清除文档级别的缓存
            cache_key = f"document_{document_id}"
            self.redis_client.delete(cache_key)
            
            # 清除每个块的缓存
            for chunk in chunks:
                chunk_cache_key = f"chunk_{chunk.id}"
                self.redis_client.delete(chunk_cache_key)
            
            logger.info(f"缓存已同步: document_id={document_id}")
            return True
            
        except Exception as e:
            logger.error(f"同步缓存错误: {e}")
            return False
    
    def _sync_versions(self, chunks: List) -> bool:
        """同步版本信息"""
        try:
            # 确保每个块的版本信息正确
            for chunk in chunks:
                # 获取最新版本
                from app.models.chunk_version import ChunkVersion
                latest_version = self.db.query(ChunkVersion).filter(
                    ChunkVersion.chunk_id == chunk.id
                ).order_by(ChunkVersion.version_number.desc()).first()
                
                # 如果版本不一致，进行修复
                if latest_version and chunk.version != latest_version.version_number:
                    chunk.version = latest_version.version_number
                    logger.info(f"修复块 {chunk.id} 的版本号: {chunk.version}")
            
            # 提交更改
            self.db.commit()
            
            logger.info("版本信息已同步")
            return True
            
        except Exception as e:
            logger.error(f"同步版本信息错误: {e}")
            self.db.rollback()
            return False
