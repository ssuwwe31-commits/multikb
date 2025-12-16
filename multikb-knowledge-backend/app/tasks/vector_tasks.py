"""
Vector Processing Tasks
"""

from celery import current_task
from app.tasks.celery_app import celery_app
from app.services.vector_service import VectorService
from app.services.ollama_service import OllamaService
from app.models.chunk import DocumentChunk
from sqlalchemy.orm import Session
from app.config.database import SessionLocal

@celery_app.task(bind=True)
def vectorize_chunk_task(self, chunk_id: int):
    """向量化文档分块任务"""
    db = SessionLocal()
    try:
        # 获取分块
        chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
        if not chunk:
            raise Exception(f"分块 {chunk_id} 不存在")
        
        # 生成向量（同步调用，无需 await）
        vector_service = VectorService(db)
        vector = vector_service.generate_embedding(chunk.content)
        
        # 这里应该将向量存储到OpenSearch
        # 暂时跳过具体实现
        
        return {"status": "success", "message": "分块向量化完成"}
        
    except Exception as e:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def vectorize_document_task(self, document_id: int):
    """向量化整个文档任务"""
    db = SessionLocal()
    try:
        # 获取文档的所有分块
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
        
        total_chunks = len(chunks)
        processed_chunks = 0
        
        vector_service = VectorService(db)
        
        for chunk in chunks:
            # 生成向量（同步调用，无需 await）
            vector = vector_service.generate_embedding(chunk.content)
            
            # 这里应该将向量存储到OpenSearch
            # 暂时跳过具体实现
            
            processed_chunks += 1
            
            # 更新进度
            progress = int((processed_chunks / total_chunks) * 100)
            current_task.update_state(
                state="PROGRESS",
                meta={"current": progress, "total": 100, "status": f"已处理 {processed_chunks}/{total_chunks} 个分块"}
            )
        
        return {"status": "success", "message": "文档向量化完成"}
        
    except Exception as e:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()

@celery_app.task
def batch_vectorize_task(chunk_ids: list):
    """批量向量化任务"""
    for chunk_id in chunk_ids:
        vectorize_chunk_task.delay(chunk_id)
    
    return {"status": "success", "message": f"已启动 {len(chunk_ids)} 个向量化任务"}
