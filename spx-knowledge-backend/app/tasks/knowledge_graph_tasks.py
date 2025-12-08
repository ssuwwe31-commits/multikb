"""
Knowledge Graph Tasks
知识图谱相关Celery任务
"""

from typing import Dict, Any, List
from datetime import datetime
from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.tasks.celery_app import celery_app
from app.config.database import SessionLocal
from app.core.logging import logger
from app.models.knowledge_graph import (
    KnowledgeGraphEntity,
    KnowledgeGraphRelationship,
    KnowledgeGraphEntityDocument,
    KnowledgeGraphExtractionTask,
)
from app.models.document import Document
from app.services.entity_extraction_service import EntityExtractionService
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.opensearch_service import OpenSearchService
from app.services.minio_storage_service import MinioStorageService
from app.services.graph_storage_service import get_graph_storage

# 确保在Celery进程中注册所有模型
import app.models  # noqa: F401


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def extract_entities_from_document_task(
    self, 
    document_id: int, 
    user_id: int
):
    """从文档中提取实体的异步任务
    
    错误处理策略：
    1. LLM调用失败：重试（最多3次）
    2. JSON解析失败：记录错误，不重试（数据质量问题）
    3. 数据库写入失败：重试（最多3次）
    4. 部分成功：保存已提取的实体，标记任务为"部分成功"
    """
    db = SessionLocal()
    extraction_task = None
    task_id = self.request.id if self else "unknown"
    
    try:
        logger.info(f"[任务ID: {task_id}] 开始提取文档 {document_id} 的实体")
        
        # 1. 获取文档
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.is_deleted == False
        ).first()
        
        if not document:
            raise ValueError(f"文档 {document_id} 不存在")
        
        # 2. 创建提取任务记录
        extraction_task = KnowledgeGraphExtractionTask(
            knowledge_base_id=document.knowledge_base_id,
            document_id=document_id,
            status="processing",
            total_entities=0,
            total_relationships=0,
        )
        db.add(extraction_task)
        db.commit()
        db.refresh(extraction_task)
        
        # 3. 获取文档内容（从MinIO或OpenSearch）
        document_content = _get_document_content(db, document)
        
        if not document_content:
            raise ValueError(f"无法获取文档 {document_id} 的内容")
        
        # 4. 调用 EntityExtractionService 提取实体
        extraction_service = EntityExtractionService(db)
        result = extraction_service.extract_with_llm(document_content, document_id)
        
        entities = result.get("entities", [])
        relationships = result.get("relationships", [])
        
        if not entities:
            logger.warning(f"[任务ID: {task_id}] 未提取到实体")
            extraction_task.status = "completed"
            extraction_task.completed_at = datetime.now()
            db.commit()
            return {
                "status": "success",
                "entities_count": 0,
                "relationships_count": 0
            }
        
        # 5. 保存实体和关系到MySQL和NebulaGraph（双写）
        nebula_storage = get_graph_storage()  # 获取图存储实例
        
        saved_entities = []
        entity_vid_map = {}  # MySQL ID -> NebulaGraph VID映射
        
        # 5.1 保存实体到MySQL
        for entity_data in entities:
            # 检查是否已存在同名实体
            existing = db.query(KnowledgeGraphEntity).filter(
                and_(
                    KnowledgeGraphEntity.knowledge_base_id == document.knowledge_base_id,
                    KnowledgeGraphEntity.name == entity_data.get("name"),
                    KnowledgeGraphEntity.type == entity_data.get("type"),
                    KnowledgeGraphEntity.is_deleted == False
                )
            ).first()
            
            if existing:
                # 更新现有实体（合并别名等）
                if entity_data.get("aliases"):
                    existing_aliases = set(existing.aliases or [])
                    new_aliases = set(entity_data.get("aliases", []))
                    existing.aliases = list(existing_aliases | new_aliases)
                saved_entities.append(existing)
            else:
                # 创建新实体
                entity = KnowledgeGraphEntity(
                    knowledge_base_id=document.knowledge_base_id,
                    user_id=user_id,
                    name=entity_data.get("name"),
                    type=entity_data.get("type"),
                    description=entity_data.get("description"),
                    aliases=entity_data.get("aliases"),
                    confidence=entity_data.get("confidence", 0.7),
                    metadata={
                        "source": f"doc_{document_id}",
                        "extraction_method": "llm"
                    },
                )
                db.add(entity)
                db.flush()  # 获取ID但不提交
                saved_entities.append(entity)
                entity_vid_map[entity.id] = f"entity_{entity.id}"
        
        db.commit()
        
        # 5.2 同步实体到NebulaGraph
        import asyncio
        space = f"kb_{document.knowledge_base_id}"
        
        for entity in saved_entities:
            try:
                vid = f"entity_{entity.id}"
                entity_vid_map[entity.id] = vid
                
                # 同步到NebulaGraph（Celery任务中需要使用asyncio.run）
                import asyncio
                asyncio.run(nebula_storage.create_entity(space, {
                    "name": entity.name,
                    "type": entity.type,
                    "description": entity.description or "",
                    "aliases": entity.aliases or [],
                    "confidence": entity.confidence,
                    "metadata": entity.metadata or {},
                    "mysql_id": entity.id,
                    "user_id": entity.user_id,
                    "id": vid
                }))
                
                # 更新同步状态
                entity.nebula_synced = True
                entity.nebula_synced_at = datetime.now()
                entity.nebula_sync_error = None
            except Exception as e:
                logger.error(f"同步实体到NebulaGraph失败: {e}, entity_id={entity.id}")
                entity.nebula_synced = False
                entity.nebula_sync_error = str(e)
        
        db.commit()
        
        # 5.3 保存关系到MySQL
        saved_relationships = []
        entity_name_map = {e.name: e.id for e in saved_entities}
        
        for rel_data in relationships:
            source_name = rel_data.get("source")
            target_name = rel_data.get("target")
            
            source_id = entity_name_map.get(source_name)
            target_id = entity_name_map.get(target_name)
            
            if not source_id or not target_id:
                logger.warning(f"关系中的实体不存在: {source_name} -> {target_name}")
                continue
            
            # 检查是否已存在相同关系
            existing = db.query(KnowledgeGraphRelationship).filter(
                and_(
                    KnowledgeGraphRelationship.source_entity_id == source_id,
                    KnowledgeGraphRelationship.target_entity_id == target_id,
                    KnowledgeGraphRelationship.relation_type == rel_data.get("relation_type"),
                    KnowledgeGraphRelationship.is_deleted == False
                )
            ).first()
            
            if existing:
                # 更新现有关系（更新权重等）
                if rel_data.get("weight"):
                    existing.weight = rel_data.get("weight")
                saved_relationships.append(existing)
            else:
                # 创建新关系
                relationship = KnowledgeGraphRelationship(
                    knowledge_base_id=document.knowledge_base_id,
                    user_id=user_id,
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relation_type=rel_data.get("relation_type"),
                    description=rel_data.get("description"),
                    weight=rel_data.get("weight", 0.5),
                    confidence=rel_data.get("confidence", 0.7),
                    metadata={
                        "source": f"doc_{document_id}",
                        "evidence": rel_data.get("evidence"),
                        "extraction_method": "llm"
                    },
                )
                db.add(relationship)
                db.flush()
                saved_relationships.append(relationship)
        
        db.commit()
        
        # 5.4 同步关系到NebulaGraph
        for relationship in saved_relationships:
            try:
                source_vid = entity_vid_map.get(relationship.source_entity_id)
                target_vid = entity_vid_map.get(relationship.target_entity_id)
                
                if source_vid and target_vid:
                    # 同步到NebulaGraph（Celery任务中需要使用asyncio.run）
                    import asyncio
                    asyncio.run(nebula_storage.create_relationship(space, source_vid, target_vid, {
                        "relation_type": relationship.relation_type,
                        "description": relationship.description or "",
                        "weight": relationship.weight,
                        "confidence": relationship.confidence,
                        "metadata": relationship.metadata or {},
                        "mysql_id": relationship.id,
                        "user_id": relationship.user_id,
                    }))
                    
                    # 更新同步状态
                    relationship.nebula_synced = True
                    relationship.nebula_synced_at = datetime.now()
                    relationship.nebula_sync_error = None
            except Exception as e:
                logger.error(f"同步关系到NebulaGraph失败: {e}, relationship_id={relationship.id}")
                relationship.nebula_synced = False
                relationship.nebula_sync_error = str(e)
        
        db.commit()
        
        # 6. 更新实体-文档关联表
        for entity in saved_entities:
            # 检查是否已存在关联
            existing_mapping = db.query(KnowledgeGraphEntityDocument).filter(
                and_(
                    KnowledgeGraphEntityDocument.entity_id == entity.id,
                    KnowledgeGraphEntityDocument.document_id == document_id,
                    KnowledgeGraphEntityDocument.is_deleted == False
                )
            ).first()
            
            if existing_mapping:
                existing_mapping.mentions_count += 1
            else:
                mapping = KnowledgeGraphEntityDocument(
                    entity_id=entity.id,
                    document_id=document_id,
                    mentions_count=1,
                )
                db.add(mapping)
        
        db.commit()
        
        # 7. 更新提取任务状态
        extraction_task.status = "completed"
        extraction_task.total_entities = len(saved_entities)
        extraction_task.total_relationships = len(saved_relationships)
        extraction_task.completed_at = datetime.now()
        db.commit()
        
        logger.info(
            f"[任务ID: {task_id}] 实体提取完成: "
            f"实体数={len(saved_entities)}, 关系数={len(saved_relationships)}"
        )
        
        return {
            "status": "success",
            "entities_count": len(saved_entities),
            "relationships_count": len(saved_relationships)
        }
        
    except Exception as exc:
        # 错误处理
        db.rollback()
        
        # 更新任务状态
        if extraction_task:
            extraction_task.status = "failed"
            extraction_task.error_message = str(exc)
            extraction_task.completed_at = datetime.now()
            db.commit()
        
        # 判断是否需要重试
        if isinstance(exc, (ConnectionError, TimeoutError)):
            # 网络错误，重试
            logger.error(f"[任务ID: {task_id}] 实体提取失败（网络错误）: {exc}")
            raise self.retry(exc=exc)
        elif isinstance(exc, ValueError):
            # 数据错误，不重试
            logger.error(f"[任务ID: {task_id}] 实体提取失败（数据错误）: {exc}")
            return {"status": "failed", "error": str(exc)}
        else:
            # 其他错误，重试
            logger.error(f"[任务ID: {task_id}] 实体提取失败: {exc}", exc_info=True)
            raise self.retry(exc=exc)
    finally:
        db.close()


def _get_document_content(db: Session, document: Document) -> str:
    """获取文档内容（从MinIO或OpenSearch）"""
    try:
        # 优先从OpenSearch获取
        opensearch_service = OpenSearchService(db)
        content = opensearch_service.get_document_content_sync(document.id)
        
        if content:
            return content
        
        # 如果OpenSearch没有，从MinIO获取
        minio_service = MinioStorageService(db)
        content = minio_service.get_document_content(document.id)
        
        return content or ""
    except Exception as e:
        logger.error(f"获取文档内容失败: {e}")
        return ""

