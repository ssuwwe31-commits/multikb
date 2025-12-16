"""
Smart Vectorization Service
根据文档修改功能设计实现智能向量化策略
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.vector_service import VectorService
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode

class SmartVectorizationService:
    """智能向量化服务 - 严格按照文档修改功能设计实现"""
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_service = VectorService(db)
        
        # 设计文档要求的策略阈值
        self.SMALL_DOCUMENT_THRESHOLD = 5    # 小文档阈值
        self.MEDIUM_DOCUMENT_THRESHOLD = 20   # 中等文档阈值
    
    def get_document_size_category(self, document_id: int) -> str:
        """获取文档大小分类 - 根据设计文档实现"""
        try:
            logger.debug(f"获取文档大小分类: document_id={document_id}")
            
            # 获取文档的块数量
            chunk_count = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).count()
            
            # 根据设计文档的策略选择
            if chunk_count <= self.SMALL_DOCUMENT_THRESHOLD:
                category = "small"
            elif chunk_count <= self.MEDIUM_DOCUMENT_THRESHOLD:
                category = "medium"
            else:
                category = "large"
            
            logger.debug(f"文档大小分类: document_id={document_id}, chunks={chunk_count}, category={category}")
            return category
            
        except Exception as e:
            logger.error(f"获取文档大小分类错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取文档大小分类失败: {str(e)}"
            )
    
    def full_document_vectorization(self, document_id: int) -> Dict[str, Any]:
        """全文档向量化 - 根据设计文档实现"""
        try:
            logger.info(f"开始全文档向量化: document_id={document_id}")
            
            # 获取文档的所有块
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index).all()
            
            if not chunks:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"文档 {document_id} 没有找到块"
                )
            
            total_chunks = len(chunks)
            processed_chunks = 0
            vectorization_results = []
            
            logger.info(f"全文档向量化: 处理 {total_chunks} 个块")
            
            # 批量向量化所有块
            for chunk in chunks:
                try:
                    # 生成向量
                    vector = self.vector_service.generate_embedding(chunk.content)
                    
                    # 保存向量结果
                    vectorization_results.append({
                        "chunk_id": chunk.id,
                        "vector": vector,
                        "vector_dimension": len(vector),
                        "success": True
                    })
                    
                    processed_chunks += 1
                    
                    logger.debug(f"块 {chunk.id} 向量化完成，向量维度: {len(vector)}")
                    
                except Exception as e:
                    logger.error(f"块 {chunk.id} 向量化失败: {e}")
                    vectorization_results.append({
                        "chunk_id": chunk.id,
                        "vector": None,
                        "vector_dimension": 0,
                        "success": False,
                        "error": str(e)
                    })
            
            success_count = sum(1 for r in vectorization_results if r["success"])
            
            result = {
                "strategy": "full_document",
                "document_id": document_id,
                "total_chunks": total_chunks,
                "processed_chunks": processed_chunks,
                "success_count": success_count,
                "failed_count": total_chunks - success_count,
                "vectorization_results": vectorization_results,
                "message": f"全文档向量化完成，成功 {success_count}/{total_chunks} 个块"
            }
            
            logger.info(f"全文档向量化完成: document_id={document_id}, 成功 {success_count}/{total_chunks}")
            return result
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"全文档向量化错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VECTOR_GENERATION_FAILED,
                message=f"全文档向量化失败: {str(e)}"
            )
    
    def contextual_vectorization(self, document_id: int, modified_chunk_id: int) -> Dict[str, Any]:
        """上下文向量化 - 根据设计文档实现"""
        try:
            logger.info(f"开始上下文向量化: document_id={document_id}, modified_chunk_id={modified_chunk_id}")
            
            # 获取修改的块
            modified_chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == modified_chunk_id,
                DocumentChunk.document_id == document_id
            ).first()
            
            if not modified_chunk:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"修改的块 {modified_chunk_id} 不存在"
                )
            
            # 获取相邻块（前后各2个块）
            adjacent_chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.chunk_index >= modified_chunk.chunk_index - 2,
                DocumentChunk.chunk_index <= modified_chunk.chunk_index + 2
            ).order_by(DocumentChunk.chunk_index).all()
            
            total_chunks = len(adjacent_chunks)
            processed_chunks = 0
            vectorization_results = []
            
            logger.info(f"上下文向量化: 处理 {total_chunks} 个相邻块")
            
            # 向量化相邻块
            for chunk in adjacent_chunks:
                try:
                    # 生成向量
                    vector = self.vector_service.generate_embedding(chunk.content)
                    
                    # 保存向量结果
                    vectorization_results.append({
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "vector": vector,
                        "vector_dimension": len(vector),
                        "success": True,
                        "is_modified": chunk.id == modified_chunk_id
                    })
                    
                    processed_chunks += 1
                    
                    logger.debug(f"相邻块 {chunk.id} 向量化完成，向量维度: {len(vector)}")
                    
                except Exception as e:
                    logger.error(f"相邻块 {chunk.id} 向量化失败: {e}")
                    vectorization_results.append({
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "vector": None,
                        "vector_dimension": 0,
                        "success": False,
                        "error": str(e),
                        "is_modified": chunk.id == modified_chunk_id
                    })
            
            success_count = sum(1 for r in vectorization_results if r["success"])
            
            result = {
                "strategy": "contextual",
                "document_id": document_id,
                "modified_chunk_id": modified_chunk_id,
                "total_chunks": total_chunks,
                "processed_chunks": processed_chunks,
                "success_count": success_count,
                "failed_count": total_chunks - success_count,
                "vectorization_results": vectorization_results,
                "message": f"上下文向量化完成，成功 {success_count}/{total_chunks} 个相邻块"
            }
            
            logger.info(f"上下文向量化完成: document_id={document_id}, 成功 {success_count}/{total_chunks}")
            return result
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"上下文向量化错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VECTOR_GENERATION_FAILED,
                message=f"上下文向量化失败: {str(e)}"
            )
    
    def incremental_vectorization(self, document_id: int, modified_chunk_id: int) -> Dict[str, Any]:
        """增量向量化 - 根据设计文档实现"""
        try:
            logger.info(f"开始增量向量化: document_id={document_id}, modified_chunk_id={modified_chunk_id}")
            
            # 获取修改的块
            modified_chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == modified_chunk_id,
                DocumentChunk.document_id == document_id
            ).first()
            
            if not modified_chunk:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"修改的块 {modified_chunk_id} 不存在"
                )
            
            vectorization_results = []
            
            try:
                # 只向量化修改的块
                vector = self.vector_service.generate_embedding(modified_chunk.content)
                
                vectorization_results.append({
                    "chunk_id": modified_chunk.id,
                    "chunk_index": modified_chunk.chunk_index,
                    "vector": vector,
                    "vector_dimension": len(vector),
                    "success": True,
                    "is_modified": True
                })
                
                logger.debug(f"修改块 {modified_chunk.id} 向量化完成，向量维度: {len(vector)}")
                
            except Exception as e:
                logger.error(f"修改块 {modified_chunk.id} 向量化失败: {e}")
                vectorization_results.append({
                    "chunk_id": modified_chunk.id,
                    "chunk_index": modified_chunk.chunk_index,
                    "vector": None,
                    "vector_dimension": 0,
                    "success": False,
                    "error": str(e),
                    "is_modified": True
                })
            
            success_count = sum(1 for r in vectorization_results if r["success"])
            
            result = {
                "strategy": "incremental",
                "document_id": document_id,
                "modified_chunk_id": modified_chunk_id,
                "total_chunks": 1,
                "processed_chunks": 1,
                "success_count": success_count,
                "failed_count": 1 - success_count,
                "vectorization_results": vectorization_results,
                "message": f"增量向量化完成，成功 {success_count}/1 个修改块"
            }
            
            logger.info(f"增量向量化完成: document_id={document_id}, 成功 {success_count}/1")
            return result
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"增量向量化错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VECTOR_GENERATION_FAILED,
                message=f"增量向量化失败: {str(e)}"
            )
    
    def smart_vectorize_document(self, document_id: int, modified_chunk_id: Optional[int] = None) -> Dict[str, Any]:
        """智能向量化 - 根据设计文档实现策略选择"""
        try:
            logger.info(f"开始智能向量化: document_id={document_id}, modified_chunk_id={modified_chunk_id}")
            
            # 获取文档大小分类
            document_category = self.get_document_size_category(document_id)
            
            logger.info(f"文档分类: document_id={document_id}, category={document_category}")
            
            # 根据设计文档的策略选择
            if document_category == "small":
                # 小文档(≤5块): 全文档向量化，保证语义一致性
                logger.info("使用全文档向量化策略")
                return self.full_document_vectorization(document_id)
                
            elif document_category == "medium":
                # 中等文档(6-20块): 上下文向量化，平衡性能和一致性
                if modified_chunk_id:
                    logger.info("使用上下文向量化策略")
                    return self.contextual_vectorization(document_id, modified_chunk_id)
                else:
                    logger.info("使用全文档向量化策略")
                    return self.full_document_vectorization(document_id)
                    
            else:  # large
                # 大文档(>20块): 增量向量化，优先性能
                if modified_chunk_id:
                    logger.info("使用增量向量化策略")
                    return self.incremental_vectorization(document_id, modified_chunk_id)
                else:
                    logger.info("使用全文档向量化策略")
                    return self.full_document_vectorization(document_id)
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"智能向量化错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VECTOR_GENERATION_FAILED,
                message=f"智能向量化失败: {str(e)}"
            )
