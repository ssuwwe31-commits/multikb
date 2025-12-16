"""
Index Processing Tasks
"""

from celery import current_task
from app.tasks.celery_app import celery_app
from app.services.vector_service import VectorService
from app.models.chunk import DocumentChunk
from app.models.document import Document
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.config.opensearch import get_opensearch

@celery_app.task(bind=True)
def index_document_task(self, document_id: int):
    """索引文档任务"""
    db = SessionLocal()
    opensearch = get_opensearch()
    
    try:
        # 获取文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise Exception(f"文档 {document_id} 不存在")
        
        # 获取文档的所有分块
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
        
        total_chunks = len(chunks)
        indexed_chunks = 0
        
        for chunk in chunks:
            # 构建索引文档
            index_doc = {
                "document_id": document_id,
                "chunk_id": chunk.id,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "chunk_type": chunk.chunk_type,
                "metadata": chunk.metadata,
                "knowledge_base_id": document.knowledge_base_id,
                "created_at": chunk.created_at.isoformat(),
                "updated_at": chunk.updated_at.isoformat(),
            }
            
            # 索引到OpenSearch
            opensearch.index(
                index="document_content",
                id=f"{document_id}_{chunk.id}",
                body=index_doc
            )
            
            indexed_chunks += 1
            
            # 更新进度
            progress = int((indexed_chunks / total_chunks) * 100)
            current_task.update_state(
                state="PROGRESS",
                meta={"current": progress, "total": 100, "status": f"已索引 {indexed_chunks}/{total_chunks} 个分块"}
            )
        
        return {"status": "success", "message": "文档索引完成"}
        
    except Exception as e:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def update_document_index_task(self, document_id: int):
    """更新文档索引任务"""
    db = SessionLocal()
    opensearch = get_opensearch()
    
    try:
        # 删除旧索引
        opensearch.delete_by_query(
            index="document_content",
            body={"query": {"term": {"document_id": document_id}}}
        )
        
        # 重新索引
        return index_document_task.delay(document_id)
        
    except Exception as e:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()

@celery_app.task
def delete_document_index_task(document_id: int):
    """删除文档索引任务"""
    opensearch = get_opensearch()
    
    try:
        # 删除文档的所有索引
        opensearch.delete_by_query(
            index="document_content",
            body={"query": {"term": {"document_id": document_id}}}
        )
        
        return {"status": "success", "message": "文档索引删除完成"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@celery_app.task
def rebuild_index_task():
    """重建索引任务"""
    db = SessionLocal()
    opensearch = get_opensearch()
    
    try:
        # 删除所有索引
        opensearch.indices.delete(index="document_content", ignore=[400, 404])
        
        # 重新创建索引
        index_mapping = {
            "mappings": {
                "properties": {
                    "document_id": {"type": "integer"},
                    "chunk_id": {"type": "integer"},
                    "content": {"type": "text"},
                    "chunk_index": {"type": "integer"},
                    "chunk_type": {"type": "keyword"},
                    "metadata": {"type": "text"},
                    "knowledge_base_id": {"type": "integer"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        }
        
        opensearch.indices.create(index="document_content", body=index_mapping)
        
        # 重新索引所有文档
        documents = db.query(Document).filter(Document.is_deleted == False).all()
        
        for document in documents:
            index_document_task.delay(document.id)
        
        return {"status": "success", "message": f"已启动 {len(documents)} 个文档的重新索引任务"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
