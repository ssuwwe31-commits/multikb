"""
Knowledge Graph API Routes
知识图谱API路由
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import asyncio
import threading

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.knowledge_graph import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse,
    EntityDetailResponse,
    RelationshipCreate,
    RelationshipUpdate,
    RelationshipResponse,
    RelationshipDetailResponse,
    PathQueryRequest,
    PathResponse,
    NeighborQueryRequest,
    ExtractionTaskCreate,
    ExtractionTaskResponse,
    VisualizationRequest,
    VisualizationResponse,
    GraphStatsResponse,
    EntityBatchCreate,
    EntityBatchUpdate,
    EntityBatchDelete,
    EntityMergeRequest,
)
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.core.response import success_response
from app.core.pagination import paginate_response

router = APIRouter()


# ============================================
# 实体相关接口
# ============================================

@router.post("/entities", response_model=dict)
async def create_entity(
    entity_data: EntityCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建实体"""
    service = KnowledgeGraphService(db)
    entity = service.create_entity(
        entity_data.knowledge_base_id,
        entity_data,
        int(current_user.get("sub"))
    )
    return success_response("实体创建成功", EntityResponse.model_validate(entity).model_dump())


@router.get("/entities", response_model=dict)
async def get_entities(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    type: Optional[str] = Query(None, description="实体类型"),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取实体列表"""
    service = KnowledgeGraphService(db)
    filters = {}
    if type:
        filters["type"] = type
    if keyword:
        filters["keyword"] = keyword
    
    entities, total = service.get_entities(
        knowledge_base_id,
        filters,
        page,
        size,
        int(current_user.get("sub"))
    )
    
    return paginate_response(
        data=entities,
        total=total,
        page=page,
        size=size
    )


@router.get("/entities/{entity_id}", response_model=dict)
async def get_entity_detail(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取实体详情"""
    from app.core.logging import logger
    import json
    service = KnowledgeGraphService(db)
    detail = service.get_entity_detail(entity_id, int(current_user.get("sub")))
    
    # 确保返回的数据结构正确
    if not detail or "entity" not in detail:
        logger.error(f"[get_entity_detail] 数据格式错误: 实体ID={entity_id}, detail={detail}")
        raise HTTPException(status_code=500, detail="实体详情数据格式错误")
    
    response = success_response("获取成功", detail)
    logger.debug(f"[get_entity_detail] 实体ID={entity_id}, 返回成功")
    return response


@router.put("/entities/{entity_id}", response_model=dict)
async def update_entity(
    entity_id: int,
    entity_data: EntityUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新实体"""
    service = KnowledgeGraphService(db)
    entity = service.update_entity(entity_id, entity_data, int(current_user.get("sub")))
    return success_response("实体更新成功", EntityResponse.model_validate(entity).model_dump())


@router.delete("/entities/{entity_id}", response_model=dict)
async def delete_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除实体"""
    service = KnowledgeGraphService(db)
    service.delete_entity(entity_id, int(current_user.get("sub")))
    return success_response("实体删除成功")


@router.post("/entities/batch", response_model=dict)
async def batch_create_entities(
    batch_data: EntityBatchCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量创建实体"""
    service = KnowledgeGraphService(db)
    created_entities = []
    for entity_data in batch_data.entities:
        entity = service.create_entity(
            entity_data.knowledge_base_id,
            entity_data,
            int(current_user.get("sub"))
        )
        created_entities.append(EntityResponse.model_validate(entity))
    return success_response("批量创建成功", {"entities": created_entities})


@router.put("/entities/batch", response_model=dict)
async def batch_update_entities(
    batch_data: EntityBatchUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量更新实体"""
    service = KnowledgeGraphService(db)
    updated_entities = []
    for entity_update in batch_data.entities:
        entity_id = entity_update.get("id")
        if not entity_id:
            continue
        update_data = EntityUpdate(**{k: v for k, v in entity_update.items() if k != "id"})
        entity = service.update_entity(entity_id, update_data, int(current_user.get("sub")))
        updated_entities.append(EntityResponse.model_validate(entity))
    return success_response("批量更新成功", {"entities": updated_entities})


@router.delete("/entities/batch", response_model=dict)
async def batch_delete_entities(
    batch_data: EntityBatchDelete,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量删除实体"""
    service = KnowledgeGraphService(db)
    deleted_count = 0
    for entity_id in batch_data.entity_ids:
        try:
            service.delete_entity(entity_id, int(current_user.get("sub")))
            deleted_count += 1
        except Exception as e:
            # 记录错误但继续处理其他实体
            pass
    return success_response("批量删除成功", {"deleted_count": deleted_count})


@router.post("/entities/merge", response_model=dict)
async def merge_entities(
    merge_data: EntityMergeRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合并实体"""
    service = KnowledgeGraphService(db)
    merged_entity = service.merge_entities(
        merge_data.entity_ids,
        merge_data.target_entity_id,
        int(current_user.get("sub"))
    )
    return success_response("实体合并成功", EntityResponse.model_validate(merged_entity).model_dump())


# ============================================
# 关系相关接口
# ============================================

@router.post("/relationships", response_model=dict)
async def create_relationship(
    relationship_data: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建关系"""
    service = KnowledgeGraphService(db)
    relationship = service.create_relationship(
        relationship_data.knowledge_base_id,
        relationship_data,
        int(current_user.get("sub"))
    )
    return success_response("关系创建成功", RelationshipResponse.model_validate(relationship).model_dump())


@router.get("/relationships", response_model=dict)
async def get_relationships(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    source_entity_id: Optional[int] = Query(None, description="源实体ID"),
    target_entity_id: Optional[int] = Query(None, description="目标实体ID"),
    relation_type: Optional[str] = Query(None, description="关系类型"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取关系列表"""
    service = KnowledgeGraphService(db)
    filters = {}
    if source_entity_id:
        filters["source_entity_id"] = source_entity_id
    if target_entity_id:
        filters["target_entity_id"] = target_entity_id
    if relation_type:
        filters["relation_type"] = relation_type
    
    relationships, total = service.get_relationships(
        knowledge_base_id,
        filters,
        page,
        size,
        int(current_user.get("sub"))
    )
    
    return paginate_response(
        data=relationships,
        total=total,
        page=page,
        size=size
    )


@router.get("/relationships/{relationship_id}", response_model=dict)
async def get_relationship_detail(
    relationship_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取关系详情"""
    service = KnowledgeGraphService(db)
    detail = service.get_relationship_detail(relationship_id, int(current_user.get("sub")))
    return success_response("获取成功", detail)


@router.put("/relationships/{relationship_id}", response_model=dict)
async def update_relationship(
    relationship_id: int,
    relationship_data: RelationshipUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新关系"""
    service = KnowledgeGraphService(db)
    relationship = service.update_relationship(relationship_id, relationship_data, int(current_user.get("sub")))
    return success_response("关系更新成功", RelationshipResponse.model_validate(relationship).model_dump())


@router.delete("/relationships/{relationship_id}", response_model=dict)
async def delete_relationship(
    relationship_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除关系"""
    service = KnowledgeGraphService(db)
    service.delete_relationship(relationship_id, int(current_user.get("sub")))
    return success_response("关系删除成功")


# ============================================
# 查询相关接口
# ============================================

@router.post("/paths", response_model=dict)
async def find_paths(
    path_query: PathQueryRequest,
    knowledge_base_id: int = Query(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """查找两个实体间的路径"""
    service = KnowledgeGraphService(db)
    paths = service.find_paths(
        knowledge_base_id,
        path_query.source_entity_id,
        path_query.target_entity_id,
        path_query.max_hops or 3,
        path_query.relation_types,
        int(current_user.get("sub"))
    )
    return success_response("路径查询成功", {"paths": paths})


@router.get("/entities/{entity_id}/neighbors", response_model=dict)
async def get_entity_neighbors(
    entity_id: int,
    knowledge_base_id: int = Query(..., description="知识库ID"),
    relation_type: Optional[str] = Query(None, description="关系类型"),
    max_depth: int = Query(1, ge=1, le=5, description="最大深度"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取实体邻居"""
    service = KnowledgeGraphService(db)
    neighbors = service.get_entity_neighbors(
        knowledge_base_id,
        entity_id,
        relation_type,
        max_depth,
        limit,
        int(current_user.get("sub"))
    )
    return success_response("获取成功", neighbors)


@router.get("/search", response_model=dict)
async def search_entities(
    q: str = Query(..., description="搜索关键词"),
    knowledge_base_id: Optional[int] = Query(None, description="知识库ID"),
    type: Optional[str] = Query(None, description="实体类型"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """搜索实体"""
    service = KnowledgeGraphService(db)
    entities = service.search_entities(q, knowledge_base_id, type, int(current_user.get("sub")), limit)
    return success_response("搜索成功", {"entities": entities})


@router.get("/visualization", response_model=dict)
async def get_visualization_data(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    entity_ids: Optional[str] = Query(None, description="实体ID列表（逗号分隔）"),
    relation_types: Optional[str] = Query(None, description="关系类型列表（逗号分隔）"),
    entity_type: Optional[str] = Query(None, description="实体类型（如：technology、person等）"),
    max_nodes: int = Query(100, ge=1, le=1000, description="最大节点数"),
    layout: str = Query("force", description="布局类型"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取可视化数据"""
    service = KnowledgeGraphService(db)
    
    # 解析参数
    entity_id_list = None
    if entity_ids:
        try:
            entity_id_list = [int(x.strip()) for x in entity_ids.split(",")]
        except ValueError:
            entity_id_list = None
    
    relation_type_list = None
    if relation_types:
        relation_type_list = [x.strip() for x in relation_types.split(",")]
    
    data = service.get_visualization_data(
        knowledge_base_id,
        entity_id_list,
        relation_type_list,
        entity_type,
        max_nodes,
        layout,
        int(current_user.get("sub"))
    )
    return success_response("获取成功", data)


# ============================================
# 提取相关接口
# ============================================

@router.post("/extract", response_model=dict)
async def extract_entities(
    extract_data: ExtractionTaskCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量提取实体"""
    from app.models.document import Document
    from app.services.permission_service import KnowledgeBasePermissionService
    from app.tasks.knowledge_graph_tasks import extract_entities_from_document_task
    
    user_id = int(current_user.get("sub"))
    
    # 检查权限
    perm_service = KnowledgeBasePermissionService(db)
    perm_service.ensure_permission(extract_data.knowledge_base_id, user_id, "kg:extract")
    
    # 获取要提取的文档列表
    query = db.query(Document).filter(
        Document.knowledge_base_id == extract_data.knowledge_base_id,
        Document.is_deleted == False
    )
    
    # 如果指定了文档ID列表，只提取这些文档
    if extract_data.document_ids:
        query = query.filter(Document.id.in_(extract_data.document_ids))
    
    documents = query.all()
    
    if not documents:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到符合条件的文档"
        )
    
    # 为每个文档创建提取任务
    task_ids = []
    entity_type_mode = extract_data.entity_type_mode or "system"
    entity_type_codes = extract_data.entity_type_codes
    for document in documents:
        task = extract_entities_from_document_task.delay(document.id, user_id, entity_type_mode, entity_type_codes)
        task_ids.append({
            "task_id": task.id,
            "document_id": document.id
        })
    
    return success_response(
        message=f"已创建 {len(task_ids)} 个提取任务",
        data={
            "tasks": task_ids,
            "total": len(task_ids)
        }
    )


@router.post("/extract/document/{document_id}", response_model=dict)
async def extract_from_document(
    document_id: int,
    entity_type_mode: Optional[str] = Query("system", description="实体类型模式: system/user/model"),
    entity_type_codes: Optional[List[str]] = Query(None, description="要提取的实体类型代码列表（可选，仅在system/user模式下有效）"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """从单个文档提取实体"""
    from app.models.document import Document
    from app.services.permission_service import KnowledgeBasePermissionService
    from app.tasks.knowledge_graph_tasks import extract_entities_from_document_task
    
    # 获取文档
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.is_deleted == False
    ).first()
    
    if not document:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    
    # 检查权限
    perm_service = KnowledgeBasePermissionService(db)
    perm_service.ensure_permission(document.knowledge_base_id, int(current_user.get("sub")), "kg:extract")
    
    # 创建提取任务
    # 验证实体类型模式
    if entity_type_mode not in ['system', 'user', 'model']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_type_mode 必须是 system, user 或 model"
        )
    
    # 验证：如果选择的是system或user模式，必须至少选择一个实体类型
    if entity_type_mode in ['system', 'user']:
        if not entity_type_codes or len(entity_type_codes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"在 {entity_type_mode} 模式下，必须至少选择一个实体类型"
            )
    
    task = extract_entities_from_document_task.delay(document_id, int(current_user.get("sub")), entity_type_mode, entity_type_codes)
    
    return success_response("提取任务已创建", {
        "task_id": task.id,
        "document_id": document_id
    })


@router.get("/extract/tasks", response_model=dict)
async def list_extraction_tasks(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取提取任务列表"""
    from app.models.knowledge_graph import KnowledgeGraphExtractionTask
    from app.services.permission_service import KnowledgeBasePermissionService
    from app.core.logging import logger
    from sqlalchemy import desc
    
    user_id = int(current_user.get("sub"))
    logger.info(f"[获取任务列表] 用户ID={user_id}, 知识库ID={knowledge_base_id}, 页码={page}, 每页数量={size}")
    
    try:
        # 检查权限
        perm_service = KnowledgeBasePermissionService(db)
        perm_service.ensure_permission(knowledge_base_id, user_id, "kg:view")
        logger.debug(f"[获取任务列表] 权限检查通过")
        
        # 查询任务列表
        query = db.query(KnowledgeGraphExtractionTask).filter(
            KnowledgeGraphExtractionTask.knowledge_base_id == knowledge_base_id,
            KnowledgeGraphExtractionTask.is_deleted == False
        )
        
        total = query.count()
        tasks = query.order_by(desc(KnowledgeGraphExtractionTask.created_at)).offset((page - 1) * size).limit(size).all()
        
        logger.info(f"[获取任务列表] 查询成功: 总数={total}, 当前页任务数={len(tasks)}")
        
        return success_response(
            message="获取成功",
            data={
                "tasks": [ExtractionTaskResponse.model_validate(task) for task in tasks],
                "total": total,
                "page": page,
                "size": size
            }
        )
    except Exception as e:
        logger.error(f"[获取任务列表] 查询失败: 知识库ID={knowledge_base_id}, 错误={e}", exc_info=True)
        raise


@router.get("/extract/tasks/{task_id}", response_model=dict)
async def get_extraction_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """查询提取任务状态"""
    from app.models.knowledge_graph import KnowledgeGraphExtractionTask
    from app.services.permission_service import KnowledgeBasePermissionService
    from app.core.logging import logger
    
    user_id = int(current_user.get("sub"))
    logger.info(f"[获取任务详情] 用户ID={user_id}, 任务ID={task_id}")
    
    try:
        task = db.query(KnowledgeGraphExtractionTask).filter(
            KnowledgeGraphExtractionTask.id == task_id,
            KnowledgeGraphExtractionTask.is_deleted == False
        ).first()
        
        if not task:
            logger.warning(f"[获取任务详情] 任务不存在: 任务ID={task_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        
        # 检查权限
        perm_service = KnowledgeBasePermissionService(db)
        perm_service.ensure_permission(task.knowledge_base_id, user_id, "kg:view")
        
        logger.info(f"[获取任务详情] 查询成功: 任务ID={task_id}, 状态={task.status}, 实体数={task.total_entities}, 关系数={task.total_relationships}")
        
        return success_response("获取成功", ExtractionTaskResponse.model_validate(task).model_dump())
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"[获取任务详情] 查询失败: 任务ID={task_id}, 错误={e}", exc_info=True)
        raise


@router.delete("/extract/tasks/{task_id}", response_model=dict)
async def delete_extraction_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除提取任务（同步删除MySQL和图数据库中的数据）"""
    from app.models.knowledge_graph import (
        KnowledgeGraphExtractionTask,
        KnowledgeGraphEntity,
        KnowledgeGraphRelationship,
        KnowledgeGraphEntityDocument
    )
    from app.services.permission_service import KnowledgeBasePermissionService
    from app.services.graph_storage_service import get_graph_storage
    from app.core.logging import logger
    
    logger.info(f"[删除任务] 开始删除任务 {task_id}, 用户ID: {current_user.get('sub')}")
    
    # 获取任务
    task = db.query(KnowledgeGraphExtractionTask).filter(
        KnowledgeGraphExtractionTask.id == task_id,
        KnowledgeGraphExtractionTask.is_deleted == False
    ).first()
    
    if not task:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    # 检查权限
    perm_service = KnowledgeBasePermissionService(db)
    perm_service.ensure_permission(task.knowledge_base_id, int(current_user.get("sub")), "kg:delete")
    
    kb_id = task.knowledge_base_id
    document_id = task.document_id
    
    logger.info(f"[删除任务] 任务信息: 知识库ID={kb_id}, 文档ID={document_id}, 状态={task.status}")
    
    try:
        # 1. 删除MySQL中的实体和关系（如果任务有对应的文档）
        if document_id:
            logger.info(f"[删除任务] 开始删除文档 {document_id} 相关的实体和关系")
            
            # 方法1：通过实体-文档关联表查找实体（更可靠）
            entity_docs = db.query(KnowledgeGraphEntityDocument).filter(
                KnowledgeGraphEntityDocument.document_id == document_id,
                KnowledgeGraphEntityDocument.is_deleted == False
            ).all()
            
            entity_ids_from_docs = [ed.entity_id for ed in entity_docs]
            logger.info(f"[删除任务] 通过实体-文档关联表找到 {len(entity_ids_from_docs)} 个实体ID")
            
            # 方法2：通过metadata中的source字段查找实体（作为补充）
            entities_from_metadata = []
            all_entities = db.query(KnowledgeGraphEntity).filter(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            ).all()
            
            logger.info(f"[删除任务] 知识库总实体数={len(all_entities)}, 目标文档ID={document_id}")
            
            # 调试：记录前几个实体的metadata内容
            sample_count = min(5, len(all_entities))
            for i, entity in enumerate(all_entities[:sample_count]):
                metadata = entity.extra_metadata or {}
                source = metadata.get("source", "") if isinstance(metadata, dict) else ""
                logger.debug(f"[删除任务] 实体示例[{i+1}]: entity_id={entity.id}, name={entity.name}, metadata类型={type(metadata)}, source={source}")
            
            for entity in all_entities:
                metadata = entity.extra_metadata or {}
                if not isinstance(metadata, dict):
                    if isinstance(metadata, str):
                        try:
                            import json
                            metadata = json.loads(metadata)
                        except:
                            continue
                    else:
                        continue
                
                source = metadata.get("source", "")
                if source:
                    source_str = str(source)
                    if source_str == f"doc_{document_id}" or \
                       source_str.startswith(f"doc_{document_id},") or \
                       source_str.endswith(f",doc_{document_id}") or \
                       f",doc_{document_id}," in source_str:
                        entities_from_metadata.append(entity.id)
                        logger.debug(f"[删除任务] 通过metadata匹配到实体: entity_id={entity.id}, name={entity.name}, source={source_str}")
            
            # 合并两种方法找到的实体ID（去重）
            all_entity_ids = list(set(entity_ids_from_docs + entities_from_metadata))
            logger.info(f"[删除任务] 合并后找到 {len(all_entity_ids)} 个唯一实体ID需要删除 (关联表:{len(entity_ids_from_docs)}, metadata:{len(entities_from_metadata)})")
            
            # 查询这些实体（确保它们属于该知识库且未删除）
            entities_to_delete = db.query(KnowledgeGraphEntity).filter(
                KnowledgeGraphEntity.id.in_(all_entity_ids),
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            ).all()
            
            logger.info(f"[删除任务] 实体匹配完成: 找到 {len(entities_to_delete)} 个相关实体需要删除")
            
            # 收集需要删除的实体ID
            entity_ids = [entity.id for entity in entities_to_delete]
            
            if entity_ids:
                # 1.1 删除实体-文档关联记录（物理删除）
                deleted_entity_docs = db.query(KnowledgeGraphEntityDocument).filter(
                    KnowledgeGraphEntityDocument.entity_id.in_(entity_ids),
                    KnowledgeGraphEntityDocument.is_deleted == False
                ).delete(synchronize_session=False)
                logger.info(f"[删除任务] 已删除 {deleted_entity_docs} 条实体-文档关联记录")
                
                # 1.2 删除关系（物理删除）
                deleted_relationships = db.query(KnowledgeGraphRelationship).filter(
                    KnowledgeGraphRelationship.knowledge_base_id == kb_id,
                    KnowledgeGraphRelationship.is_deleted == False,
                    (
                        KnowledgeGraphRelationship.source_entity_id.in_(entity_ids) |
                        KnowledgeGraphRelationship.target_entity_id.in_(entity_ids)
                    )
                ).delete(synchronize_session=False)
                logger.info(f"[删除任务] 已物理删除 {deleted_relationships} 个相关关系")
                
                # 1.3 删除实体（物理删除）
                deleted_entities = db.query(KnowledgeGraphEntity).filter(
                    KnowledgeGraphEntity.id.in_(entity_ids),
                    KnowledgeGraphEntity.is_deleted == False
                ).delete(synchronize_session=False)
                logger.info(f"[删除任务] 已物理删除 {deleted_entities} 个实体")
                
                # 提交MySQL的删除操作（先提交，快速返回响应）
                db.commit()
                logger.info(f"[删除任务] MySQL数据删除完成")
                
                # 2. 在后台异步批量删除NebulaGraph中的数据（不阻塞响应）
                # 将NebulaGraph删除移到后台执行，避免前端超时
                vids = [f"entity_{entity_id}" for entity_id in entity_ids]
                space = f"kb_{kb_id}"
                
                async def background_delete_nebula():
                    """后台异步批量删除NebulaGraph实体"""
                    try:
                        nebula_storage = get_graph_storage()
                        logger.info(f"[删除任务-后台] 开始从NebulaGraph批量删除 {len(vids)} 个实体")
                        result = await nebula_storage.batch_delete_entities(space, vids)
                        logger.info(f"[删除任务-后台] NebulaGraph批量删除完成: 成功={result['success']}, 失败={result['failed']}")
                    except Exception as e:
                        logger.error(f"[删除任务-后台] NebulaGraph批量删除失败: {e}", exc_info=True)
                
                # 使用asyncio.create_task在后台执行（不等待完成）
                try:
                    asyncio.create_task(background_delete_nebula())
                    logger.info(f"[删除任务] 已启动后台任务批量删除NebulaGraph数据: {len(vids)}个实体")
                except RuntimeError:
                    # 如果没有事件循环，使用新线程执行
                    def run_in_thread():
                        try:
                            asyncio.run(background_delete_nebula())
                        except Exception as e:
                            logger.error(f"[删除任务-后台] 后台删除任务执行失败: {e}", exc_info=True)
                    thread = threading.Thread(target=run_in_thread, daemon=True)
                    thread.start()
                    logger.info(f"[删除任务] 已启动后台线程批量删除NebulaGraph数据: {len(vids)}个实体")
            else:
                logger.info(f"[删除任务] 没有找到需要删除的实体")
        else:
            logger.info(f"[删除任务] 任务没有关联文档，跳过数据删除步骤")
        
        # 3. 删除任务记录（物理删除）
        db.delete(task)
        db.commit()
        
        logger.info(f"[删除任务] 任务 {task_id} 删除完成")
        
        return success_response("任务删除成功")
    except Exception as e:
        logger.error(f"[删除任务] 删除任务失败: 任务ID={task_id}, 错误={e}", exc_info=True)
        db.rollback()
        raise


@router.post("/extract/tasks/{task_id}/regenerate", response_model=dict)
async def regenerate_extraction_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """重新生成提取任务（先删除，后重新生成）"""
    from app.models.knowledge_graph import (
        KnowledgeGraphExtractionTask,
        KnowledgeGraphEntity,
        KnowledgeGraphRelationship,
        KnowledgeGraphEntityDocument
    )
    from app.services.permission_service import KnowledgeBasePermissionService
    from app.tasks.knowledge_graph_tasks import extract_entities_from_document_task
    from app.services.graph_storage_service import get_graph_storage
    from app.core.logging import logger
    
    logger.info(f"[重新生成任务] 开始重新生成任务 {task_id}, 用户ID: {current_user.get('sub')}")
    
    # 获取任务
    task = db.query(KnowledgeGraphExtractionTask).filter(
        KnowledgeGraphExtractionTask.id == task_id,
        KnowledgeGraphExtractionTask.is_deleted == False
    ).first()
    
    if not task:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    # 检查权限
    perm_service = KnowledgeBasePermissionService(db)
    perm_service.ensure_permission(task.knowledge_base_id, int(current_user.get("sub")), "kg:extract")
    
    if not task.document_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该任务没有关联文档，无法重新生成"
        )
    
    document_id = task.document_id
    user_id = int(current_user.get("sub"))
    kb_id = task.knowledge_base_id
    
    logger.info(f"[重新生成任务] 任务信息: 知识库ID={kb_id}, 文档ID={document_id}, 当前状态={task.status}")
    
    try:
        # 1. 先删除任务相关的数据（同步删除MySQL和图数据库中的数据）
        logger.info(f"[重新生成任务] 步骤1: 删除现有任务和数据")
        
        # 方法1：通过实体-文档关联表查找实体（更可靠）
        entity_docs = db.query(KnowledgeGraphEntityDocument).filter(
            KnowledgeGraphEntityDocument.document_id == document_id,
            KnowledgeGraphEntityDocument.is_deleted == False
        ).all()
        
        entity_ids_from_docs = [ed.entity_id for ed in entity_docs]
        logger.info(f"[重新生成任务] 通过实体-文档关联表找到 {len(entity_ids_from_docs)} 个实体ID")
        
        # 方法2：通过metadata中的source字段查找实体（作为补充）
        entities_from_metadata = []
        all_entities = db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.knowledge_base_id == kb_id,
            KnowledgeGraphEntity.is_deleted == False
        ).all()
        
        logger.info(f"[重新生成任务] 知识库总实体数={len(all_entities)}, 目标文档ID={document_id}")
        
        # 调试：记录前几个实体的metadata内容
        sample_count = min(5, len(all_entities))
        for i, entity in enumerate(all_entities[:sample_count]):
            metadata = entity.extra_metadata or {}
            source = metadata.get("source", "") if isinstance(metadata, dict) else ""
            logger.debug(f"[重新生成任务] 实体示例[{i+1}]: entity_id={entity.id}, name={entity.name}, metadata类型={type(metadata)}, source={source}")
        
        for entity in all_entities:
            metadata = entity.extra_metadata or {}
            if not isinstance(metadata, dict):
                if isinstance(metadata, str):
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except:
                        continue
                else:
                    continue
            
            source = metadata.get("source", "")
            if source:
                source_str = str(source)
                if source_str == f"doc_{document_id}" or \
                   source_str.startswith(f"doc_{document_id},") or \
                   source_str.endswith(f",doc_{document_id}") or \
                   f",doc_{document_id}," in source_str:
                    entities_from_metadata.append(entity.id)
                    logger.debug(f"[重新生成任务] 通过metadata匹配到实体: entity_id={entity.id}, name={entity.name}, source={source_str}")
        
        # 合并两种方法找到的实体ID（去重）
        all_entity_ids = list(set(entity_ids_from_docs + entities_from_metadata))
        logger.info(f"[重新生成任务] 合并后找到 {len(all_entity_ids)} 个唯一实体ID需要删除 (关联表:{len(entity_ids_from_docs)}, metadata:{len(entities_from_metadata)})")
        
        # 查询这些实体（确保它们属于该知识库且未删除）
        entities_to_delete = db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.id.in_(all_entity_ids),
            KnowledgeGraphEntity.knowledge_base_id == kb_id,
            KnowledgeGraphEntity.is_deleted == False
        ).all()
        
        logger.info(f"[重新生成任务] 实体匹配完成: 找到 {len(entities_to_delete)} 个相关实体需要删除")
        
        # 收集需要删除的实体ID
        entity_ids = [entity.id for entity in entities_to_delete]
        
        if entity_ids:
            # 1.1 删除实体-文档关联记录（物理删除）
            deleted_entity_docs = db.query(KnowledgeGraphEntityDocument).filter(
                KnowledgeGraphEntityDocument.entity_id.in_(entity_ids),
                KnowledgeGraphEntityDocument.is_deleted == False
            ).delete(synchronize_session=False)
            logger.info(f"[重新生成任务] 已删除 {deleted_entity_docs} 条实体-文档关联记录")
            
            # 1.2 删除关系（物理删除）
            deleted_relationships = db.query(KnowledgeGraphRelationship).filter(
                KnowledgeGraphRelationship.knowledge_base_id == kb_id,
                KnowledgeGraphRelationship.is_deleted == False,
                (
                    KnowledgeGraphRelationship.source_entity_id.in_(entity_ids) |
                    KnowledgeGraphRelationship.target_entity_id.in_(entity_ids)
                )
            ).delete(synchronize_session=False)
            logger.info(f"[重新生成任务] 已物理删除 {deleted_relationships} 个相关关系")
            
            # 1.3 删除实体（物理删除）
            deleted_entities = db.query(KnowledgeGraphEntity).filter(
                KnowledgeGraphEntity.id.in_(entity_ids),
                KnowledgeGraphEntity.is_deleted == False
            ).delete(synchronize_session=False)
            logger.info(f"[重新生成任务] 已物理删除 {deleted_entities} 个实体")
            
            # 提交MySQL的删除操作（先提交，快速返回响应）
            db.commit()
            logger.info(f"[重新生成任务] MySQL数据删除完成")
            
            # 2. 在后台异步批量删除NebulaGraph中的数据（不阻塞响应）
            vids = [f"entity_{entity_id}" for entity_id in entity_ids]
            space = f"kb_{kb_id}"
            
            async def background_delete_nebula():
                """后台异步批量删除NebulaGraph实体"""
                try:
                    nebula_storage = get_graph_storage()
                    logger.info(f"[重新生成任务-后台] 开始从NebulaGraph批量删除 {len(vids)} 个实体")
                    result = await nebula_storage.batch_delete_entities(space, vids)
                    logger.info(f"[重新生成任务-后台] NebulaGraph批量删除完成: 成功={result['success']}, 失败={result['failed']}")
                except Exception as e:
                    logger.error(f"[重新生成任务-后台] NebulaGraph批量删除失败: {e}", exc_info=True)
            
            # 使用asyncio.create_task在后台执行（不等待完成）
            try:
                asyncio.create_task(background_delete_nebula())
                logger.info(f"[重新生成任务] 已启动后台任务批量删除NebulaGraph数据: {len(vids)}个实体")
            except RuntimeError:
                # 如果没有事件循环，使用新线程执行
                def run_in_thread():
                    try:
                        asyncio.run(background_delete_nebula())
                    except Exception as e:
                        logger.error(f"[重新生成任务-后台] 后台删除任务执行失败: {e}", exc_info=True)
                thread = threading.Thread(target=run_in_thread, daemon=True)
                thread.start()
                logger.info(f"[重新生成任务] 已启动后台线程批量删除NebulaGraph数据: {len(vids)}个实体")
        else:
            logger.info(f"[重新生成任务] 没有找到需要删除的实体")
        
        # 删除任务记录（物理删除）
        db.delete(task)
        db.commit()
        
        logger.info(f"[重新生成任务] 步骤1完成: 已删除任务和数据")
        
        # 2. 重新创建提取任务（使用默认的system模式，或从任务metadata中获取）
        entity_type_mode = "system"  # 默认使用系统类型
        entity_type_codes = None
        if task.extra_metadata and isinstance(task.extra_metadata, dict):
            entity_type_mode = task.extra_metadata.get("entity_type_mode", "system")
            entity_type_codes = task.extra_metadata.get("entity_type_codes")
        
        logger.info(f"[重新生成任务] 步骤2: 创建新的提取任务, 文档ID={document_id}, 用户ID={user_id}, 模式={entity_type_mode}")
        new_task = extract_entities_from_document_task.delay(document_id, user_id, entity_type_mode, entity_type_codes)
        
        logger.info(f"[重新生成任务] 任务 {task_id} 重新生成完成, 新任务ID: {new_task.id}, 文档ID: {document_id}")
        
        return success_response(
            message="任务重新生成成功",
            data={
                "old_task_id": task_id,
                "new_task_id": new_task.id,
                "document_id": document_id
            }
        )
    except Exception as e:
        logger.error(f"[重新生成任务] 重新生成任务失败: 任务ID={task_id}, 文档ID={document_id}, 错误={e}", exc_info=True)
        db.rollback()
        raise


# ============================================
# 统计信息接口
# ============================================

@router.get("/stats", response_model=dict)
async def get_graph_stats(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取知识图谱统计信息"""
    service = KnowledgeGraphService(db)
    stats = service.get_graph_stats(knowledge_base_id, int(current_user.get("sub")))
    return success_response("获取成功", stats)


@router.post("/cleanup/orphaned-data", response_model=dict)
async def cleanup_orphaned_data(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """清理NebulaGraph中的孤立数据（MySQL中不存在的实体和关系）"""
    from app.services.graph_storage_service import get_graph_storage
    from app.core.logging import logger
    from app.services.permission_service import KnowledgeBasePermissionService
    import asyncio
    
    logger.info(f"[清理孤立数据] 开始清理知识库 {knowledge_base_id} 的孤立数据, 用户ID: {current_user.get('sub')}")
    
    # 检查权限
    perm_service = KnowledgeBasePermissionService(db)
    perm_service.ensure_permission(knowledge_base_id, int(current_user.get("sub")), "kg:delete")
    
    try:
        # 获取MySQL中有效的实体ID列表
        from app.models.knowledge_graph import KnowledgeGraphEntity
        valid_entity_ids = set(
            row[0] for row in db.query(KnowledgeGraphEntity.id).filter(
                KnowledgeGraphEntity.knowledge_base_id == knowledge_base_id,
                KnowledgeGraphEntity.is_deleted == False
            ).all()
        )
        
        logger.info(f"[清理孤立数据] MySQL中有效实体数量: {len(valid_entity_ids)}")
        
        if not valid_entity_ids:
            logger.info(f"[清理孤立数据] MySQL中没有有效实体，清理NebulaGraph中所有数据")
            valid_entity_ids = set()  # 空集合，将清理所有数据
        
        nebula_storage = get_graph_storage()
        space = f"kb_{knowledge_base_id}"
        
        # 确保图空间存在（如果不存在则创建）
        await nebula_storage.create_space_if_not_exists(space)
        
        # 查询NebulaGraph中所有实体
        query_all_entities_nGQL = """
        MATCH (n:entity)
        RETURN id(n) as vid, n.mysql_id as mysql_id, n.name as name
        LIMIT 10000;
        """
        logger.debug(f"[清理孤立数据] 查询所有实体的nGQL: {query_all_entities_nGQL}")
        all_entities = await nebula_storage._execute(query_all_entities_nGQL, space=space)
        
        logger.info(f"[清理孤立数据] NebulaGraph中实体总数: {len(all_entities)}")
        
        # 找出孤立实体（mysql_id不在有效列表中的，或者mysql_id为0/NULL的）
        orphaned_vids = []
        valid_vids = []
        
        for entity in all_entities:
            vid = str(entity.get('vid', '')).strip('"\'')
            mysql_id_raw = entity.get('mysql_id', 0)
            
            # 处理mysql_id
            mysql_id = 0
            if mysql_id_raw:
                if isinstance(mysql_id_raw, str):
                    if mysql_id_raw.upper() not in ('__NULL__', 'NULL', 'NONE', ''):
                        try:
                            mysql_id = int(mysql_id_raw)
                        except (ValueError, TypeError):
                            mysql_id = 0
                elif isinstance(mysql_id_raw, (int, float)):
                    mysql_id = int(mysql_id_raw)
            
            # 判断是否是孤立实体
            if mysql_id == 0 or mysql_id not in valid_entity_ids:
                orphaned_vids.append(vid)
                logger.debug(f"[清理孤立数据] 发现孤立实体: vid={vid}, mysql_id={mysql_id}, name={entity.get('name', '')}")
            else:
                valid_vids.append(vid)
        
        logger.info(f"[清理孤立数据] 孤立实体数量: {len(orphaned_vids)}, 有效实体数量: {len(valid_vids)}")
        
        # 删除孤立实体（会自动删除相关的关系）
        deleted_count = 0
        failed_count = 0
        
        if orphaned_vids:
            logger.info(f"[清理孤立数据] 开始删除 {len(orphaned_vids)} 个孤立实体")
            for idx, vid in enumerate(orphaned_vids):
                try:
                    await nebula_storage.delete_entity(space, vid)
                    deleted_count += 1
                    # 每删除10个记录一次进度，或前10个都记录
                    if deleted_count % 10 == 0 or deleted_count <= 10:
                        logger.info(f"[清理孤立数据] 删除进度: {deleted_count}/{len(orphaned_vids)}, 当前vid={vid}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"[清理孤立数据] 删除孤立实体失败: vid={vid}, 错误={e}")
                    # 如果失败太多，记录警告
                    if failed_count > len(orphaned_vids) * 0.1:  # 失败率超过10%
                        logger.warning(f"[清理孤立数据] 删除失败率较高: 失败={failed_count}, 总数={len(orphaned_vids)}")
        else:
            logger.info(f"[清理孤立数据] 没有发现孤立实体，无需清理")
        
        logger.info(f"[清理孤立数据] 清理完成: 总实体数={len(all_entities)}, 孤立实体数={len(orphaned_vids)}, "
                   f"成功删除={deleted_count}, 失败={failed_count}")
        
        return success_response(
            message="清理完成",
            data={
                "total_entities": len(all_entities),
                "orphaned_count": len(orphaned_vids),
                "deleted_count": deleted_count,
                "failed_count": failed_count
            }
        )
    except Exception as e:
        logger.error(f"[清理孤立数据] 清理失败: {e}", exc_info=True)
        raise

