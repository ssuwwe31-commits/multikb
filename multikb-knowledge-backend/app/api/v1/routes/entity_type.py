"""
Entity Type API Routes
实体类型管理API路由
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.entity_type import (
    EntityTypeCreate,
    EntityTypeUpdate,
    EntityTypeResponse,
    KnowledgeBaseEntityTypeConfigRequest,
    KnowledgeBaseEntityTypeConfigUpdate,
    IndustryTemplateResponse,
    ApplyTemplateRequest,
)
from app.services.entity_type_service import EntityTypeService
from app.core.response import success_response
from app.core.logging import logger

router = APIRouter()


# ============================================
# 辅助函数
# ============================================

def entity_type_to_dict(entity_type, include_children: bool = False, service: Optional[EntityTypeService] = None) -> Dict[str, Any]:
    """将 EntityType 模型转换为字典，避免 SQLAlchemy metadata 属性冲突"""
    result = {
        "id": entity_type.id,
        "code": entity_type.code,
        "name": entity_type.name,
        "description": entity_type.description,
        "icon": entity_type.icon,
        "color": entity_type.color,
        "tag_type": entity_type.tag_type,
        "sort_order": entity_type.sort_order,
        "is_system": entity_type.is_system,
        "is_enabled": entity_type.is_enabled,
        "user_id": entity_type.user_id,  # 创建用户ID
        "parent_id": entity_type.parent_id,
        "level": entity_type.level,
        "metadata": entity_type.meta_data,  # 使用 meta_data 字段，但输出为 metadata
        "created_at": entity_type.created_at,
        "updated_at": entity_type.updated_at
    }
    
    # 如果需要包含子类型
    if include_children:
        if service:
            # 使用服务加载子类型
            children = service.get_children_types(entity_type.id)
            result["children"] = [entity_type_to_dict(child, include_children=False, service=service) for child in children]
        elif hasattr(entity_type, 'children') and entity_type.children:
            # 如果已经加载了子类型关系
            result["children"] = [entity_type_to_dict(child, include_children=False, service=service) for child in entity_type.children]
        else:
            result["children"] = []
    else:
        result["children"] = []
    
    return result


# ============================================
# 实体类型管理接口
# ============================================

@router.get("/entity-types", response_model=dict)
async def get_entity_types(
    is_enabled: Optional[bool] = Query(None, description="是否只返回启用的类型"),
    is_system: Optional[bool] = Query(None, description="是否只返回系统类型"),
    knowledge_base_id: Optional[int] = Query(None, description="知识库ID（返回该知识库可用的类型）"),
    level: Optional[int] = Query(None, description="层级（1=一级分类，2=二级分类，3=三级分类，最多3级）"),
    parent_id: Optional[int] = Query(None, description="父类型ID（返回该父类型下的子类型）"),
    include_children: bool = Query(False, description="是否包含子类型"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=1000, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（搜索名称或代码）"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取实体类型列表（支持层级查询和分页）"""
    from app.core.pagination import paginate_response
    
    service = EntityTypeService(db)
    user_id = int(current_user.get("sub", 0)) if current_user else None
    types, total = service.get_all_types_paginated(
        is_enabled=is_enabled,
        is_system=is_system,
        knowledge_base_id=knowledge_base_id,
        level=level,
        parent_id=parent_id,
        include_children=include_children,
        user_id=user_id,
        keyword=keyword,
        page=page,
        size=size
    )
    
    # 手动构建响应数据，避免 SQLAlchemy metadata 属性冲突
    type_list = [entity_type_to_dict(t, include_children=include_children, service=service) for t in types]
    
    return success_response(
        "获取成功",
        paginate_response(type_list, total, page, size)
    )


@router.get("/entity-types/tree", response_model=dict)
async def get_entity_type_tree(
    root_id: Optional[int] = Query(None, description="根类型ID（可选，不指定则返回所有一级分类）"),
    knowledge_base_id: Optional[int] = Query(None, description="知识库ID（可选）"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取实体类型树（包含所有子类型）"""
    service = EntityTypeService(db)
    user_id = int(current_user.get("sub", 0)) if current_user else None
    tree = service.get_type_tree(root_id=root_id, knowledge_base_id=knowledge_base_id, user_id=user_id)
    
    return success_response(
        "获取成功",
        {"tree": tree, "total": len(tree)}
    )


@router.get("/entity-types/{type_id}", response_model=dict)
async def get_entity_type(
    type_id: int,
    include_children: bool = Query(False, description="是否包含子类型"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取单个实体类型详情"""
    service = EntityTypeService(db)
    entity_type = service.get_type_by_id(type_id)
    
    if not entity_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实体类型不存在")
    
    return success_response(
        "获取成功",
        entity_type_to_dict(entity_type, include_children=include_children, service=service)
    )


@router.get("/entity-types/{type_id}/children", response_model=dict)
async def get_entity_type_children(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取指定类型的子类型列表"""
    service = EntityTypeService(db)
    children = service.get_children_types(type_id)
    
    type_list = [entity_type_to_dict(t, include_children=False, service=service) for t in children]
    
    return success_response(
        "获取成功",
        {"types": type_list, "total": len(type_list)}
    )


@router.post("/entity-types", response_model=dict)
async def create_entity_type(
    type_data: EntityTypeCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建实体类型（用户自定义）"""
    service = EntityTypeService(db)
    user_id = int(current_user.get("sub", 0)) if current_user else None
    entity_type = service.create_type(type_data.model_dump(), user_id=user_id)
    
    # 使用辅助函数避免 SQLAlchemy metadata 属性冲突
    return success_response(
        "创建成功",
        entity_type_to_dict(entity_type, include_children=False, service=service)
    )


@router.put("/entity-types/{type_id}", response_model=dict)
async def update_entity_type(
    type_id: int,
    type_data: EntityTypeUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新实体类型"""
    service = EntityTypeService(db)
    user_id = int(current_user.get("sub", 0)) if current_user else None
    entity_type = service.update_type(type_id, type_data.model_dump(exclude_unset=True), user_id=user_id)
    
    # 使用辅助函数避免 SQLAlchemy metadata 属性冲突
    return success_response(
        "更新成功",
        entity_type_to_dict(entity_type, include_children=False, service=service)
    )


@router.delete("/entity-types/{type_id}", response_model=dict)
async def delete_entity_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除实体类型"""
    service = EntityTypeService(db)
    user_id = int(current_user.get("sub", 0)) if current_user else None
    service.delete_type(type_id, user_id=user_id)
    
    return success_response("删除成功")


@router.patch("/entity-types/{type_id}/toggle", response_model=dict)
async def toggle_entity_type(
    type_id: int,
    is_enabled: bool = Query(..., description="是否启用"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """启用/禁用实体类型"""
    # TODO: 添加管理员权限检查
    service = EntityTypeService(db)
    entity_type = service.toggle_type(type_id, is_enabled)
    
    # 使用辅助函数避免 SQLAlchemy metadata 属性冲突
    return success_response(
        f"{'启用' if is_enabled else '禁用'}成功",
        entity_type_to_dict(entity_type, include_children=False, service=service)
    )


# ============================================
# 知识库实体类型配置接口
# ============================================

@router.get("/knowledge-bases/{kb_id}/entity-types", response_model=dict)
async def get_knowledge_base_entity_types(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取知识库的实体类型配置"""
    service = EntityTypeService(db)
    types = service.get_knowledge_base_types(kb_id)
    
    type_list = [entity_type_to_dict(t) for t in types]
    
    return success_response(
        "获取成功",
        {"types": type_list, "total": len(type_list)}
    )


@router.post("/knowledge-bases/{kb_id}/entity-types", response_model=dict)
async def configure_knowledge_base_entity_types(
    kb_id: int,
    config_data: KnowledgeBaseEntityTypeConfigRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """配置知识库的实体类型"""
    # TODO: 添加知识库编辑权限检查
    service = EntityTypeService(db)
    
    configs = None
    if config_data.configs:
        configs = [c.model_dump() for c in config_data.configs]
    
    kb_entity_types = service.configure_knowledge_base_types(
        kb_id,
        config_data.entity_type_ids,
        configs
    )
    
    return success_response(
        "配置成功",
        {"count": len(kb_entity_types)}
    )


# ============================================
# 行业模板接口
# ============================================

@router.get("/entity-type-templates", response_model=dict)
async def get_industry_templates(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取所有行业模板列表"""
    service = EntityTypeService(db)
    templates = service.get_industry_templates()
    
    return success_response(
        "获取成功",
        {"templates": templates, "total": len(templates)}
    )


@router.get("/entity-type-templates/{template_code}", response_model=dict)
async def get_industry_template(
    template_code: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取指定行业模板详情"""
    service = EntityTypeService(db)
    template = service.get_industry_template(template_code)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板 '{template_code}' 不存在"
        )
    
    # 获取模板中的实体类型详情
    entity_types = []
    for et_def in template["entity_types"]:
        entity_type = service.get_type_by_code(et_def["code"])
        if entity_type:
            type_dict = entity_type_to_dict(entity_type)
            type_dict["sort_order"] = et_def.get("sort_order", 0)
            entity_types.append(type_dict)
        else:
            # 如果类型不存在，返回基本信息
            entity_types.append({
                "code": et_def["code"],
                "name": et_def.get("name", et_def["code"]),
                "exists": False,
                "sort_order": et_def.get("sort_order", 0)
            })
    
    return success_response(
        "获取成功",
        {
            "template": {
                "code": template["code"],
                "name": template["name"],
                "description": template["description"]
            },
            "entity_types": entity_types
        }
    )


@router.post("/knowledge-bases/{kb_id}/apply-template", response_model=dict)
async def apply_industry_template(
    kb_id: int,
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """应用行业模板到知识库"""
    # TODO: 添加知识库编辑权限检查
    service = EntityTypeService(db)
    
    # 先创建模板中定义的实体类型（如果不存在）
    try:
        service.create_template_entity_types(request.template_code)
    except Exception as e:
        logger.warning(f"创建模板实体类型失败（可能已存在）: {e}")
    
    # 应用模板
    kb_entity_types = service.apply_industry_template(kb_id, request.template_code)
    
    return success_response(
        f"模板 '{request.template_code}' 应用成功",
        {"count": len(kb_entity_types)}
    )

