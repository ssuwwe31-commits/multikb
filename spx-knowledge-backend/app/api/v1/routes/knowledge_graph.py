"""
Knowledge Graph API Routes
知识图谱API路由
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
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
    current_user: User = Depends(get_current_user),
):
    """创建实体"""
    service = KnowledgeGraphService(db)
    entity = service.create_entity(
        entity_data.knowledge_base_id,
        entity_data,
        current_user.id
    )
    return success_response(data=EntityResponse.model_validate(entity).model_dump())


@router.get("/entities", response_model=dict)
async def get_entities(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    type: Optional[str] = Query(None, description="实体类型"),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        current_user.id
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
    current_user: User = Depends(get_current_user),
):
    """获取实体详情"""
    service = KnowledgeGraphService(db)
    detail = service.get_entity_detail(entity_id, current_user.id)
    return success_response(data=detail)


@router.put("/entities/{entity_id}", response_model=dict)
async def update_entity(
    entity_id: int,
    entity_data: EntityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新实体"""
    service = KnowledgeGraphService(db)
    entity = service.update_entity(entity_id, entity_data, current_user.id)
    return success_response(data=EntityResponse.model_validate(entity).model_dump())


@router.delete("/entities/{entity_id}", response_model=dict)
async def delete_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除实体"""
    service = KnowledgeGraphService(db)
    service.delete_entity(entity_id, current_user.id)
    return success_response(message="实体删除成功")


@router.post("/entities/batch", response_model=dict)
async def batch_create_entities(
    batch_data: EntityBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量创建实体"""
    service = KnowledgeGraphService(db)
    created_entities = []
    for entity_data in batch_data.entities:
        entity = service.create_entity(
            entity_data.knowledge_base_id,
            entity_data,
            current_user.id
        )
        created_entities.append(EntityResponse.model_validate(entity).model_dump())
    return success_response(data={"entities": created_entities})


@router.put("/entities/batch", response_model=dict)
async def batch_update_entities(
    batch_data: EntityBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量更新实体"""
    service = KnowledgeGraphService(db)
    updated_entities = []
    for entity_update in batch_data.entities:
        entity_id = entity_update.get("id")
        if not entity_id:
            continue
        update_data = EntityUpdate(**{k: v for k, v in entity_update.items() if k != "id"})
        entity = service.update_entity(entity_id, update_data, current_user.id)
        updated_entities.append(EntityResponse.model_validate(entity).model_dump())
    return success_response(data={"entities": updated_entities})


@router.delete("/entities/batch", response_model=dict)
async def batch_delete_entities(
    batch_data: EntityBatchDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除实体"""
    service = KnowledgeGraphService(db)
    deleted_count = 0
    for entity_id in batch_data.entity_ids:
        try:
            service.delete_entity(entity_id, current_user.id)
            deleted_count += 1
        except Exception as e:
            # 记录错误但继续处理其他实体
            pass
    return success_response(data={"deleted_count": deleted_count})


@router.post("/entities/merge", response_model=dict)
async def merge_entities(
    merge_data: EntityMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """合并实体"""
    service = KnowledgeGraphService(db)
    merged_entity = service.merge_entities(
        merge_data.entity_ids,
        merge_data.target_entity_id,
        current_user.id
    )
    return success_response(data=EntityResponse.model_validate(merged_entity).model_dump())


# ============================================
# 关系相关接口
# ============================================

@router.post("/relationships", response_model=dict)
async def create_relationship(
    relationship_data: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建关系"""
    service = KnowledgeGraphService(db)
    relationship = service.create_relationship(
        relationship_data.knowledge_base_id,
        relationship_data,
        current_user.id
    )
    return success_response(data=RelationshipResponse.model_validate(relationship).model_dump())


@router.get("/relationships", response_model=dict)
async def get_relationships(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    source_entity_id: Optional[int] = Query(None, description="源实体ID"),
    target_entity_id: Optional[int] = Query(None, description="目标实体ID"),
    relation_type: Optional[str] = Query(None, description="关系类型"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        current_user.id
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
    current_user: User = Depends(get_current_user),
):
    """获取关系详情"""
    service = KnowledgeGraphService(db)
    detail = service.get_relationship_detail(relationship_id, current_user.id)
    return success_response(data=detail)


@router.put("/relationships/{relationship_id}", response_model=dict)
async def update_relationship(
    relationship_id: int,
    relationship_data: RelationshipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新关系"""
    service = KnowledgeGraphService(db)
    relationship = service.update_relationship(relationship_id, relationship_data, current_user.id)
    return success_response(data=RelationshipResponse.model_validate(relationship).model_dump())


@router.delete("/relationships/{relationship_id}", response_model=dict)
async def delete_relationship(
    relationship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除关系"""
    service = KnowledgeGraphService(db)
    service.delete_relationship(relationship_id, current_user.id)
    return success_response(message="关系删除成功")


# ============================================
# 查询相关接口
# ============================================

@router.post("/paths", response_model=dict)
async def find_paths(
    path_query: PathQueryRequest,
    knowledge_base_id: int = Query(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查找两个实体间的路径"""
    service = KnowledgeGraphService(db)
    paths = service.find_paths(
        knowledge_base_id,
        path_query.source_entity_id,
        path_query.target_entity_id,
        path_query.max_hops or 3,
        path_query.relation_types,
        current_user.id
    )
    return success_response(data={"paths": paths})


@router.get("/entities/{entity_id}/neighbors", response_model=dict)
async def get_entity_neighbors(
    entity_id: int,
    knowledge_base_id: int = Query(..., description="知识库ID"),
    relation_type: Optional[str] = Query(None, description="关系类型"),
    max_depth: int = Query(1, ge=1, le=5, description="最大深度"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取实体邻居"""
    service = KnowledgeGraphService(db)
    neighbors = service.get_entity_neighbors(
        knowledge_base_id,
        entity_id,
        relation_type,
        max_depth,
        limit,
        current_user.id
    )
    return success_response(data=neighbors)


@router.get("/search", response_model=dict)
async def search_entities(
    q: str = Query(..., description="搜索关键词"),
    knowledge_base_id: Optional[int] = Query(None, description="知识库ID"),
    type: Optional[str] = Query(None, description="实体类型"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索实体"""
    service = KnowledgeGraphService(db)
    entities = service.search_entities(q, knowledge_base_id, type, current_user.id, limit)
    return success_response(data={"entities": entities})


@router.get("/visualization", response_model=dict)
async def get_visualization_data(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    entity_ids: Optional[str] = Query(None, description="实体ID列表（逗号分隔）"),
    relation_types: Optional[str] = Query(None, description="关系类型列表（逗号分隔）"),
    max_nodes: int = Query(100, ge=1, le=1000, description="最大节点数"),
    layout: str = Query("force", description="布局类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        max_nodes,
        layout,
        current_user.id
    )
    return success_response(data=data)


# ============================================
# 提取相关接口
# ============================================

@router.post("/extract", response_model=dict)
async def extract_entities(
    extract_data: ExtractionTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量提取实体"""
    # TODO: 实现实体提取任务创建
    return success_response(message="实体提取功能待实现")


@router.post("/extract/document/{document_id}", response_model=dict)
async def extract_from_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    perm_service.ensure_permission(document.knowledge_base_id, current_user.id, "kg:extract")
    
    # 创建提取任务
    task = extract_entities_from_document_task.delay(document_id, current_user.id)
    
    return success_response(data={
        "task_id": task.id,
        "document_id": document_id,
        "message": "提取任务已创建"
    })


@router.get("/extract/tasks/{task_id}", response_model=dict)
async def get_extraction_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询提取任务状态"""
    from app.models.knowledge_graph import KnowledgeGraphExtractionTask
    
    task = db.query(KnowledgeGraphExtractionTask).filter(
        KnowledgeGraphExtractionTask.id == task_id,
        KnowledgeGraphExtractionTask.is_deleted == False
    ).first()
    
    if not task:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    # 检查权限
    from app.services.permission_service import KnowledgeBasePermissionService
    perm_service = KnowledgeBasePermissionService(db)
    perm_service.ensure_permission(task.knowledge_base_id, current_user.id, "kg:view")
    
    return success_response(data=ExtractionTaskResponse.model_validate(task).model_dump())


# ============================================
# 统计信息接口
# ============================================

@router.get("/stats", response_model=dict)
async def get_graph_stats(
    knowledge_base_id: int = Query(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识图谱统计信息"""
    service = KnowledgeGraphService(db)
    stats = service.get_graph_stats(knowledge_base_id, current_user.id)
    return success_response(data=stats)

