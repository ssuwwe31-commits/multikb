"""
Knowledge Graph Tasks
知识图谱相关Celery任务
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

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
from app.config.settings import settings

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
    user_id: int,
    entity_type_mode: str = "system",
    entity_type_codes: Optional[List[str]] = None
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
            extra_metadata={
                "entity_type_mode": entity_type_mode,
                "entity_type_codes": entity_type_codes
            }  # 保存实体类型模式和代码列表
        )
        db.add(extraction_task)
        db.commit()
        db.refresh(extraction_task)
        
        # 3. 获取文档内容（从MinIO或OpenSearch）
        document_content = _get_document_content(db, document)
        
        if not document_content:
            raise ValueError(f"无法获取文档 {document_id} 的内容")
        
        # 4. 调用 EntityExtractionService 提取实体
        logger.info(f"[任务ID: {task_id}] 开始提取实体，模式={entity_type_mode}，文档内容长度={len(document_content)} 字符")
        if entity_type_codes:
            logger.info(f"[任务ID: {task_id}] 指定了实体类型代码列表: {entity_type_codes}")
        extraction_service = EntityExtractionService(db)
        result = asyncio.run(extraction_service.extract_with_llm(
            document_content, 
            document_id,
            knowledge_base_id=document.knowledge_base_id,
            entity_type_mode=entity_type_mode,
            entity_type_codes=entity_type_codes
        ))
        
        entities = result.get("entities", [])
        relationships = result.get("relationships", [])
        logger.info(f"[任务ID: {task_id}] 提取完成: {len(entities)} 个实体, {len(relationships)} 个关系")
        
        # 验证实体数据，确保没有null值
        valid_entities = []
        invalid_entities = []
        for idx, entity in enumerate(entities):
            name = entity.get("name")
            entity_type = entity.get("type")
            
            # 验证必填字段
            if not name or not isinstance(name, str) or not name.strip():
                logger.warning(f"[任务ID: {task_id}] 跳过无效实体[{idx}]: name为空或不是字符串, entity_data={entity}")
                invalid_entities.append(entity)
                continue
            
            if not entity_type or not isinstance(entity_type, str) or not entity_type.strip():
                logger.warning(f"[任务ID: {task_id}] 跳过无效实体[{idx}]: type为空或不是字符串, name={name}, entity_data={entity}")
                invalid_entities.append(entity)
                continue
            
            # 清理和标准化数据
            clean_entity = {
                "name": str(name).strip(),
                "type": str(entity_type).strip(),
                "description": str(entity.get("description", "")).strip() if entity.get("description") else "",
                "aliases": entity.get("aliases") if isinstance(entity.get("aliases"), list) else [],
                "confidence": float(entity.get("confidence", settings.KG_ENTITY_DEFAULT_CONFIDENCE)) if entity.get("confidence") is not None else settings.KG_ENTITY_DEFAULT_CONFIDENCE,
                "metadata": entity.get("metadata", {}) if isinstance(entity.get("metadata"), dict) else {}
            }
            
            # 确保aliases列表中没有null值
            clean_entity["aliases"] = [str(alias).strip() for alias in clean_entity["aliases"] if alias and str(alias).strip()]
            
            valid_entities.append(clean_entity)
        
        if invalid_entities:
            logger.warning(f"[任务ID: {task_id}] 实体验证: 有效={len(valid_entities)}, 无效={len(invalid_entities)}")
        # 减少验证完成的详细日志（已注释）
        # else:
        #     logger.debug(f"[任务ID: {task_id}] 实体验证完成: 有效={len(valid_entities)}")
        entities = valid_entities  # 使用验证后的实体列表
        
        if not entities:
            logger.warning(f"[任务ID: {task_id}] 验证后没有有效实体")
            extraction_task.status = "completed"
            extraction_task.completed_at = datetime.now()
            db.commit()
            return {
                "status": "success",
                "entities_count": 0,
                "relationships_count": 0
            }
        
        # 5. 保存实体和关系（优先存储到NebulaGraph，MySQL只存储索引信息）
        nebula_storage = get_graph_storage()  # 获取图存储实例
        space = f"kb_{document.knowledge_base_id}"
        
        saved_entities = []
        entity_vid_map = {}  # MySQL ID -> NebulaGraph VID映射
        
        # 5.1 优先保存实体到NebulaGraph（如果启用）
        if settings.USE_NEBULA_GRAPH:
            logger.info(f"[任务ID: {task_id}] 开始保存 {len(entities)} 个实体")
            created_count = 0
            updated_count = 0
            for idx, entity_data in enumerate(entities):
                try:
                    # 检查MySQL中是否已存在相同名称和类型的实体（物理删除后，只会找到未删除的实体）
                    existing = db.query(KnowledgeGraphEntity).filter(
                        and_(
                            KnowledgeGraphEntity.knowledge_base_id == document.knowledge_base_id,
                            KnowledgeGraphEntity.name == entity_data.get("name"),
                            KnowledgeGraphEntity.type == entity_data.get("type"),
                            KnowledgeGraphEntity.is_deleted == False
                        )
                    ).first()
                    
                    if existing:
                        entity_id = existing.id
                        vid = f"entity_{entity_id}"
                        updated_count += 1
                        
                        # 更新NebulaGraph中的实体（合并别名等）
                        # 确保existing.aliases不是None
                        existing_aliases_list = existing.aliases if existing.aliases is not None else []
                        if entity_data.get("aliases") and isinstance(entity_data.get("aliases"), list):
                            existing_aliases = set(existing_aliases_list)
                            new_aliases = set(entity_data.get("aliases", []))
                            merged_aliases = list(existing_aliases | new_aliases)
                            # 清理null值
                            merged_aliases = [str(alias).strip() for alias in merged_aliases if alias and str(alias).strip()]
                        else:
                            merged_aliases = existing_aliases_list
                            # 清理null值
                            merged_aliases = [str(alias).strip() for alias in merged_aliases if alias and str(alias).strip()]
                        
                        # 确保description不是None
                        entity_description = str(entity_data.get("description", "")).strip() if entity_data.get("description") else ""
                        existing_description = str(existing.description).strip() if existing.description else ""
                        final_description = entity_description if entity_description else existing_description
                        
                        # 确保confidence不是None
                        entity_confidence = float(entity_data.get("confidence", settings.KG_ENTITY_DEFAULT_CONFIDENCE)) if entity_data.get("confidence") is not None else settings.KG_ENTITY_DEFAULT_CONFIDENCE
                        existing_confidence = float(existing.confidence) if existing.confidence is not None else settings.KG_ENTITY_DEFAULT_CONFIDENCE
                        final_confidence = entity_confidence if entity_data.get("confidence") is not None else existing_confidence
                        
                        # 确保metadata是字典
                        entity_metadata = entity_data.get("metadata", {}) if isinstance(entity_data.get("metadata"), dict) else {}
                        existing_metadata = existing.extra_metadata if isinstance(existing.extra_metadata, dict) else {}
                        final_metadata = {**existing_metadata, **entity_metadata} if entity_metadata else existing_metadata
                        
                        # 更新NebulaGraph实体（确保没有null值）
                        nebula_update_data = {
                            "name": str(existing.name).strip(),
                            "type": str(existing.type).strip(),
                            "description": final_description,  # 确保是字符串，不是None
                            "aliases": merged_aliases,  # 确保是列表，没有null值
                            "confidence": final_confidence,  # 确保是数字，不是None
                            "metadata": final_metadata,  # 确保是字典
                            "mysql_id": entity_id,
                            "user_id": existing.user_id if existing.user_id else 0,
                            "id": vid
                        }
                        
                        asyncio.run(nebula_storage.create_entity(space, nebula_update_data))
                        
                        # 更新MySQL中的基础字段（用于快速查询和展示）
                        if entity_data.get("aliases"):
                            existing.aliases = merged_aliases
                        if entity_data.get("description"):
                            existing.description = entity_data.get("description")
                        existing.nebula_synced = True
                        existing.nebula_synced_at = datetime.now()
                        saved_entities.append(existing)
                        
                        # 只有在成功保存后才更新映射
                        entity_vid_map[entity_id] = vid
                    else:
                        # 创建新实体：先写入MySQL获取ID（存储基础索引信息，用于快速查询）
                        entity_name = str(entity_data.get("name", "")).strip()
                        entity_type = str(entity_data.get("type", "")).strip()
                        entity_description = str(entity_data.get("description", "")).strip() if entity_data.get("description") else ""
                        entity_aliases = entity_data.get("aliases", [])
                        if not isinstance(entity_aliases, list):
                            entity_aliases = []
                        entity_confidence = float(entity_data.get("confidence", settings.KG_ENTITY_DEFAULT_CONFIDENCE)) if entity_data.get("confidence") is not None else settings.KG_ENTITY_DEFAULT_CONFIDENCE
                        
                        # 再次验证（双重保险）
                        if not entity_name:
                            logger.error(f"[任务ID: {task_id}] 实体名称为空，跳过: entity_data={entity_data}")
                            continue
                        if not entity_type:
                            logger.error(f"[任务ID: {task_id}] 实体类型为空，跳过: name={entity_name}, entity_data={entity_data}")
                            continue
                        
                        # 尝试创建新实体，如果失败（可能由于并发插入导致唯一约束冲突），则获取现有实体
                        try:
                            entity = KnowledgeGraphEntity(
                                knowledge_base_id=document.knowledge_base_id,
                                user_id=user_id,
                                name=entity_name,
                                type=entity_type,
                                description=entity_description if entity_description else None,  # MySQL存储描述用于快速展示和搜索
                                aliases=entity_aliases if entity_aliases else [],  # MySQL存储别名用于快速搜索
                                confidence=entity_confidence,
                                extra_metadata={
                                    "source": f"doc_{document_id}",
                                    "extraction_method": "llm",
                                    "stored_in": "nebula"  # 标记完整数据存储在NebulaGraph
                                },
                            )

                            db.add(entity)
                            db.flush()  # 获取ID但不提交
                            entity_id = entity.id
                            vid = f"entity_{entity_id}"
                            created_count += 1
                        except IntegrityError as e:
                            # 捕获唯一约束冲突（可能由于并发插入导致）
                            db.rollback()
                            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                            if "Duplicate entry" in error_msg and "uk_kb_name_type" in error_msg:
                                logger.warning(f"[任务ID: {task_id}] 实体创建时发生唯一约束冲突（可能并发插入），尝试获取现有实体: name={entity_name}, type={entity_type}")
                                # 重新查询现有实体（可能在检查后到插入之间被其他进程创建）
                                existing = db.query(KnowledgeGraphEntity).filter(
                                    and_(
                                        KnowledgeGraphEntity.knowledge_base_id == document.knowledge_base_id,
                                        KnowledgeGraphEntity.name == entity_name,
                                        KnowledgeGraphEntity.type == entity_type,
                                        KnowledgeGraphEntity.is_deleted == False
                                    )
                                ).first()
                                
                                if existing:
                                    entity_id = existing.id
                                    vid = f"entity_{entity_id}"
                                    entity = existing
                                    updated_count += 1
                                    
                                    # 合并元数据中的source
                                    existing_metadata = existing.extra_metadata if isinstance(existing.extra_metadata, dict) else {}
                                    new_metadata = {
                                        "source": f"doc_{document_id}",
                                        "extraction_method": "llm",
                                        "stored_in": "nebula"
                                    }
                                    # 如果source已存在，合并（可能是多个文档）
                                    if "source" in existing_metadata:
                                        existing_sources = existing_metadata.get("source", "")
                                        if isinstance(existing_sources, str):
                                            existing_sources = [existing_sources] if existing_sources else []
                                        elif not isinstance(existing_sources, list):
                                            existing_sources = []
                                        # 添加新的source（如果不存在）
                                        new_source = f"doc_{document_id}"
                                        if new_source not in existing_sources:
                                            existing_sources.append(new_source)
                                        new_metadata["source"] = ",".join(existing_sources) if len(existing_sources) > 1 else existing_sources[0] if existing_sources else new_source
                                    
                                    existing.extra_metadata = {**existing_metadata, **new_metadata}
                                    
                                    # 更新描述和别名（如果新数据更完整）
                                    if entity_description and (not existing.description or len(entity_description) > len(existing.description or "")):
                                        existing.description = entity_description
                                    if entity_aliases:
                                        existing_aliases = existing.aliases if existing.aliases else []
                                        merged_aliases = list(set(existing_aliases) | set(entity_aliases))
                                        existing.aliases = merged_aliases
                                    if entity_confidence > (existing.confidence or 0):
                                        existing.confidence = entity_confidence
                                    
                                    db.flush()  # 确保更新被保存
                                    
                                    # 使用合并后的数据更新NebulaGraph（复用existing分支的逻辑）
                                    # 合并别名
                                    existing_aliases_list = existing.aliases if existing.aliases is not None else []
                                    if entity_aliases and isinstance(entity_aliases, list):
                                        existing_aliases = set(existing_aliases_list)
                                        new_aliases = set(entity_aliases)
                                        merged_aliases = list(existing_aliases | new_aliases)
                                        merged_aliases = [str(alias).strip() for alias in merged_aliases if alias and str(alias).strip()]
                                    else:
                                        merged_aliases = existing_aliases_list
                                        merged_aliases = [str(alias).strip() for alias in merged_aliases if alias and str(alias).strip()]
                                    
                                    # 合并描述
                                    final_description = existing.description if existing.description else entity_description
                                    
                                    # 合并置信度
                                    final_confidence = max(existing.confidence or settings.KG_ENTITY_DEFAULT_CONFIDENCE, entity_confidence)
                                    
                                    # 合并元数据（使用已合并的metadata）
                                    final_metadata = existing.extra_metadata if isinstance(existing.extra_metadata, dict) else {}
                                    
                                    # 更新NebulaGraph实体
                                    nebula_update_data = {
                                        "name": str(existing.name).strip(),
                                        "type": str(existing.type).strip(),
                                        "description": final_description or "",
                                        "aliases": merged_aliases,
                                        "confidence": final_confidence,
                                        "metadata": final_metadata,
                                        "mysql_id": entity_id,
                                        "user_id": existing.user_id if existing.user_id else user_id,
                                        "id": vid
                                    }
                                    
                                    asyncio.run(nebula_storage.create_entity(space, nebula_update_data))
                                    
                                    # 更新MySQL同步状态
                                    existing.nebula_synced = True
                                    existing.nebula_synced_at = datetime.now()
                                    saved_entities.append(existing)
                                    
                                    # 只有在成功保存后才更新映射
                                    entity_vid_map[entity_id] = vid
                                    
                                    # 跳过后续的创建逻辑
                                    continue
                                else:
                                    # 如果还是找不到，这是一个严重错误
                                    logger.error(f"[任务ID: {task_id}] 唯一约束冲突但找不到现有实体，这不应该发生: name={entity_name}, type={entity_type}")
                                    raise Exception(f"无法创建或获取实体: {entity_name} ({entity_type})")
                            else:
                                # 其他类型的IntegrityError，重新抛出
                                raise
                        
                        # 这是新创建的实体，准备插入NebulaGraph的数据（确保没有null值）
                        nebula_entity_data = {
                            "name": entity_name,
                            "type": entity_type,
                            "description": entity_description,  # 已经是空字符串，不会是null
                            "aliases": entity_aliases,  # 确保是列表
                            "confidence": entity_confidence,
                            "metadata": {
                                "source": f"doc_{document_id}",
                                "extraction_method": "llm"
                            },
                            "mysql_id": entity_id,
                            "user_id": user_id,
                            "id": vid
                        }
                        
                        # 写入NebulaGraph（完整数据）
                        asyncio.run(nebula_storage.create_entity(space, nebula_entity_data))
                        
                        entity.nebula_synced = True
                        entity.nebula_synced_at = datetime.now()
                        saved_entities.append(entity)
                        
                        # 只有在成功保存后才更新映射
                        entity_vid_map[entity_id] = vid
                except Exception as e:
                    logger.error(f"[任务ID: {task_id}] 保存实体到NebulaGraph失败: entity_name={entity_data.get('name')}, entity_type={entity_data.get('type')}, 错误={e}", exc_info=True)
                    db.rollback()
                    raise Exception(f"保存实体到NebulaGraph失败: {str(e)}")
            
            # 实体保存完成，输出汇总
            logger.info(f"[任务ID: {task_id}] 实体保存完成: 创建={created_count}, 更新={updated_count}, 总计={len(saved_entities)}")
            
            db.commit()
        else:
            # 必须启用NebulaGraph，不允许使用MySQL存储
            db.rollback()
            raise Exception("NebulaGraph未启用，无法提取实体。请启用NebulaGraph后再试。")
        
        # 5.3 保存关系（优先存储到NebulaGraph，MySQL只存储索引信息）
        logger.info(f"[任务ID: {task_id}] 开始保存 {len(relationships)} 个关系")
        
        # 验证关系数据，确保没有null值
        valid_relationships = []
        invalid_relationships = []
        entity_name_map = {e.name: e.id for e in saved_entities}
        
        for idx, rel_data in enumerate(relationships):
            source_name = rel_data.get("source")
            target_name = rel_data.get("target")
            relation_type = rel_data.get("relation_type")
            
            # 验证必填字段
            if not source_name or not isinstance(source_name, str) or not source_name.strip():
                logger.warning(f"[任务ID: {task_id}] 跳过无效关系[{idx}]: source为空或不是字符串, rel_data={rel_data}")
                invalid_relationships.append(rel_data)
                continue
            
            if not target_name or not isinstance(target_name, str) or not target_name.strip():
                logger.warning(f"[任务ID: {task_id}] 跳过无效关系[{idx}]: target为空或不是字符串, source={source_name}, rel_data={rel_data}")
                invalid_relationships.append(rel_data)
                continue
            
            if not relation_type or not isinstance(relation_type, str) or not relation_type.strip():
                logger.warning(f"[任务ID: {task_id}] 跳过无效关系[{idx}]: relation_type为空或不是字符串, source={source_name}, target={target_name}, rel_data={rel_data}")
                invalid_relationships.append(rel_data)
                continue
            
            # 清理和标准化数据
            clean_rel = {
                "source": str(source_name).strip(),
                "target": str(target_name).strip(),
                "relation_type": str(relation_type).strip(),
                "description": str(rel_data.get("description", "")).strip() if rel_data.get("description") else "",
                "weight": float(rel_data.get("weight", 0.5)) if rel_data.get("weight") is not None else 0.5,
                "confidence": float(rel_data.get("confidence", settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE)) if rel_data.get("confidence") is not None else settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE,
                "evidence": str(rel_data.get("evidence", "")).strip() if rel_data.get("evidence") else "",
                "metadata": rel_data.get("metadata", {}) if isinstance(rel_data.get("metadata"), dict) else {}
            }
            
            valid_relationships.append(clean_rel)
        
        if invalid_relationships:
            logger.warning(f"[任务ID: {task_id}] 关系验证: 有效={len(valid_relationships)}, 无效={len(invalid_relationships)}")
        # 减少验证完成的详细日志（已注释）
        # else:
        #     logger.debug(f"[任务ID: {task_id}] 关系验证完成: 有效={len(valid_relationships)}")
        
        saved_relationships = []
        rel_created_count = 0
        rel_updated_count = 0
        for rel_data in valid_relationships:
            source_name = rel_data.get("source")
            target_name = rel_data.get("target")
            
            source_id = entity_name_map.get(source_name)
            target_id = entity_name_map.get(target_name)
            
            if not source_id or not target_id:
                logger.warning(f"[任务ID: {task_id}] 关系中的实体不存在: source={source_name} (id={source_id}), target={target_name} (id={target_id}), 跳过该关系")
                continue
            
            source_vid = entity_vid_map.get(source_id)
            target_vid = entity_vid_map.get(target_id)
            
            if not source_vid or not target_vid:
                logger.warning(f"[任务ID: {task_id}] 关系中的实体VID不存在: source_id={source_id} (vid={source_vid}), target_id={target_id} (vid={target_vid}), 跳过该关系")
                continue
            
            # 优先写入NebulaGraph（如果启用）
            if settings.USE_NEBULA_GRAPH:
                try:
                    # 先检查MySQL中是否已存在（用于获取ID）
                    existing = db.query(KnowledgeGraphRelationship).filter(
                        and_(
                            KnowledgeGraphRelationship.source_entity_id == source_id,
                            KnowledgeGraphRelationship.target_entity_id == target_id,
                            KnowledgeGraphRelationship.relation_type == rel_data.get("relation_type"),
                            KnowledgeGraphRelationship.is_deleted == False
                        )
                    ).first()
                    
                    if existing:
                        rel_id = existing.id
                        rel_updated_count += 1
                        
                        # 确保数据没有null值
                        rel_type = str(rel_data.get("relation_type", "")).strip() if rel_data.get("relation_type") else str(existing.relation_type).strip()
                        rel_description = str(rel_data.get("description", "")).strip() if rel_data.get("description") else ""
                        rel_weight = float(rel_data.get("weight", 0.5)) if rel_data.get("weight") is not None else (float(existing.weight) if existing.weight is not None else 0.5)
                        rel_confidence = float(rel_data.get("confidence", settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE)) if rel_data.get("confidence") is not None else (float(existing.confidence) if existing.confidence is not None else settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE)
                        rel_metadata = rel_data.get("metadata", {}) if isinstance(rel_data.get("metadata"), dict) else {}
                        existing_metadata = existing.extra_metadata if isinstance(existing.extra_metadata, dict) else {}
                        final_metadata = {**existing_metadata, **rel_metadata} if rel_metadata else existing_metadata
                        
                        # 更新NebulaGraph中的关系（确保没有null值）
                        nebula_update_rel_data = {
                            "relation_type": rel_type,
                            "description": rel_description,  # 确保是字符串，不是None
                            "weight": rel_weight,  # 确保是数字，不是None
                            "confidence": rel_confidence,  # 确保是数字，不是None
                            "metadata": final_metadata,  # 确保是字典
                            "mysql_id": rel_id,
                            "user_id": existing.user_id if existing.user_id else 0,
                        }
                        
                        asyncio.run(nebula_storage.create_relationship(space, source_vid, target_vid, nebula_update_rel_data))
                        existing.nebula_synced = True
                        existing.nebula_synced_at = datetime.now()
                        saved_relationships.append(existing)
                    else:
                        # 创建新关系：先写入MySQL获取ID（仅存储索引信息）
                        relation_type = str(rel_data.get("relation_type", "")).strip()
                        rel_weight = float(rel_data.get("weight", 0.5)) if rel_data.get("weight") is not None else 0.5
                        rel_confidence = float(rel_data.get("confidence", settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE)) if rel_data.get("confidence") is not None else settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE
                        
                        relationship = KnowledgeGraphRelationship(
                            knowledge_base_id=document.knowledge_base_id,
                            user_id=user_id,
                            source_entity_id=source_id,
                            target_entity_id=target_id,
                            relation_type=relation_type,
                            description=None,  # MySQL不存储详细描述
                            weight=rel_weight,
                            confidence=rel_confidence,
                            extra_metadata={
                                "source": f"doc_{document_id}",
                                "stored_in": "nebula"  # 标记数据存储在NebulaGraph
                            },
                        )
                        db.add(relationship)
                        db.flush()
                        rel_id = relationship.id
                        rel_created_count += 1
                        
                        # 准备插入NebulaGraph的关系数据（确保没有null值）
                        nebula_rel_data = {
                            "relation_type": relation_type,
                            "description": str(rel_data.get("description", "")).strip() if rel_data.get("description") else "",
                            "weight": rel_weight,
                            "confidence": rel_confidence,
                            "metadata": {
                                "source": f"doc_{document_id}",
                                "evidence": str(rel_data.get("evidence", "")).strip() if rel_data.get("evidence") else "",
                                "extraction_method": "llm"
                            },
                            "mysql_id": rel_id,
                            "user_id": user_id,
                        }
                        
                        # 写入NebulaGraph（完整数据）
                        asyncio.run(nebula_storage.create_relationship(space, source_vid, target_vid, nebula_rel_data))
                        
                        relationship.nebula_synced = True
                        relationship.nebula_synced_at = datetime.now()
                        saved_relationships.append(relationship)
                except Exception as e:
                    logger.error(f"[任务ID: {task_id}] 保存关系到NebulaGraph失败: source={source_name}, target={target_name}, "
                               f"source_vid={source_vid}, target_vid={target_vid}, 错误={e}", exc_info=True)
                    db.rollback()
                    raise Exception(f"保存关系到NebulaGraph失败: {str(e)}")
        
        # 关系保存完成，输出汇总
        logger.info(f"[任务ID: {task_id}] 关系保存完成: 创建={rel_created_count}, 更新={rel_updated_count}, 总计={len(saved_relationships)}")
        
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
    """获取文档完整文本内容（从MinIO的parsed/content.json获取）
    
    注意：实体提取应该从原始文档的完整文本内容进行提取，而不是从已经分块的chunks。
    实体提取服务内部会根据8000字符进行分块处理。
    """
    try:
        minio_service = MinioStorageService()
        created_at = document.created_at if hasattr(document, 'created_at') and document.created_at else datetime.now()
        year = created_at.strftime("%Y")
        month = created_at.strftime("%m")
        
        # 方法1：优先从parsed/content.json获取完整文本内容
        content_path = f"documents/{year}/{month}/{document.id}/parsed/content.json"
        try:
            obj = minio_service.client.get_object(minio_service.bucket_name, content_path)
            import json
            content_data = json.loads(obj.read().decode('utf-8'))
            obj.close()
            obj.release_conn()
            
            # 提取text_content字段（这是文档的完整文本内容）
            if isinstance(content_data, dict):
                text_content = content_data.get("text_content", "") or content_data.get("text", "") or content_data.get("content", "")
                if text_content:
                    logger.info(f"从MinIO content.json获取文档 {document.id} 完整文本内容成功，长度={len(text_content)} 字符")
                    return text_content
        except Exception as e:
            logger.debug(f"从MinIO content.json获取失败: {e}")
        
        # 方法2：如果content.json没有，尝试从原始文件重新解析
        # 获取原始文件路径
        original_file_path = None
        if hasattr(document, 'file_path') and document.file_path:
            original_file_path = document.file_path
        elif hasattr(document, 'storage_path') and document.storage_path:
            original_file_path = document.storage_path
        
        if original_file_path:
            try:
                # 下载原始文件到临时目录
                import tempfile
                import os
                file_bytes = minio_service.download_file(original_file_path)
                
                # 根据文件类型选择解析器
                file_type = getattr(document, 'file_type', '') or ''
                file_suffix = file_type.lower() if file_type else ''
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_suffix}" if file_suffix else "") as tmp_file:
                    tmp_file.write(file_bytes)
                    tmp_file_path = tmp_file.name
                
                try:
                    # 根据文件类型解析
                    if file_suffix == 'pdf':
                        from app.services.pdf_service import PdfService
                        parser = PdfService(db)
                    elif file_suffix in ['doc', 'docx']:
                        from app.services.docx_service import DocxService
                        parser = DocxService(db)
                    elif file_suffix in ['txt', 'log']:
                        from app.services.txt_service import TxtService
                        parser = TxtService(db)
                    elif file_suffix == 'md':
                        from app.services.markdown_service import MarkdownService
                        parser = MarkdownService(db)
                    else:
                        logger.warning(f"不支持的文件类型: {file_suffix}，尝试使用TxtService")
                        from app.services.txt_service import TxtService
                        parser = TxtService(db)
                    
                    parse_result = parser.parse_document(tmp_file_path)
                    if parse_result:
                        text_content = parse_result.get('text_content', '')
                        if text_content:
                            logger.info(f"从原始文件解析获取文档 {document.id} 完整文本内容成功，长度={len(text_content)} 字符")
                            return text_content
                finally:
                    # 清理临时文件
                    try:
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"从原始文件解析获取失败: {e}")
        
        logger.warning(f"无法获取文档 {document.id} 的完整文本内容")
        return ""
    except Exception as e:
        logger.error(f"获取文档内容失败: {e}", exc_info=True)
        return ""

