"""
Knowledge Base API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
)
from app.core.response import success_response
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.knowledge_base_category_service import KnowledgeBaseCategoryService
from app.services.permission_service import KnowledgeBasePermissionService
from app.models.knowledge_base_category import KnowledgeBaseCategory
from app.models.knowledge_base_member import KnowledgeBaseMember
from app.models.user import User
from app.dependencies.database import get_db
from sqlalchemy.orm import Session
from app.core.logging import logger

router = APIRouter()

def _update_kb_visibility_if_needed(db: Session, kb_id: int):
    """
    根据成员数量自动更新知识库的 visibility 字段
    - 如果有成员（除了owner），设置为 shared
    - 如果只有owner一个人，设置为 private
    """
    try:
        from app.models.knowledge_base import KnowledgeBase
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return
        
        # 统计成员数量（包括owner）
        member_count = db.query(KnowledgeBaseMember).filter(
            KnowledgeBaseMember.knowledge_base_id == kb_id
        ).count()
        
        # 如果成员数量 > 1（有除了owner之外的成员），设置为 shared
        # 如果成员数量 <= 1（只有owner），设置为 private
        new_visibility = "shared" if member_count > 1 else "private"
        
        if kb.visibility != new_visibility:
            kb.visibility = new_visibility
            db.commit()
            logger.info(f"知识库 {kb_id} 的 visibility 已自动更新为 {new_visibility}（成员数: {member_count}）")
    except Exception as e:
        logger.warning(f"自动更新知识库 visibility 失败: kb_id={kb_id}, error={e}", exc_info=True)
        # 不影响主流程，只记录警告

def get_current_user_id(request: Request) -> int:
    """从请求中获取当前用户ID（由中间件设置）"""
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户信息")
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户ID")

@router.get("/")
async def get_knowledge_bases(
    request: Request,
    page: int = 1,
    size: int = 20,
    require_permission: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取知识库列表（分页）
    
    Args:
        page: 页码
        size: 每页大小
        require_permission: 可选，要求用户对该知识库有指定权限（如 'doc:upload'）
                          只有拥有该权限的知识库才会被返回
    """
    # 获取当前用户ID
    user_id = get_current_user_id(request)
    service = KnowledgeBaseService(db)
    items, total = await service.get_knowledge_bases_paginated(
        page=page, 
        size=size, 
        user_id=user_id,
        require_permission=require_permission
    )
    # 兼容部分前端对 {code, message, data} 的期望结构
    return {
        "code": 0,
        "message": "ok",
        "data": {"list": items, "total": total, "page": page, "size": size}
    }

@router.post("/")
async def create_knowledge_base(
    request: Request,
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """创建知识库"""
    # 获取当前用户ID
    user_id = get_current_user_id(request)
    # 允许通过 category_name 动态创建或复用分类；分类为必填
    kb_data = knowledge_base.dict(exclude_unset=True)
    # 设置用户ID（数据隔离）
    kb_data["user_id"] = user_id
    # 校验分类
    if not kb_data.get("category_id") and not (kb_data.get("category_name") and kb_data.get("category_name").strip()):
        return {"code": 400, "message": "分类必填", "data": None}
    # 保留名称（创建时必填）
    if not kb_data.get("category_id") and kb_data.get("category_name"):
        name = kb_data.get("category_name").strip()
        if name:
            existing = db.query(KnowledgeBaseCategory).filter(
                KnowledgeBaseCategory.name == name,
                KnowledgeBaseCategory.is_deleted == False
            ).first()
            if existing:
                kb_data["category_id"] = existing.id
            else:
                cat_service = KnowledgeBaseCategoryService(db)
                created = cat_service.create_category({"name": name})
                kb_data["category_id"] = created["id"]
    kb_data.pop("category_name", None)
    service = KnowledgeBaseService(db)
    kb = await service.create_knowledge_base(KnowledgeBaseCreate.parse_obj(kb_data), user_id=user_id)
    # 创建成功后，为 owner 补充一条成员记录（幂等处理）
    try:
        member = (
            db.query(KnowledgeBaseMember)
            .filter(
                KnowledgeBaseMember.knowledge_base_id == kb.id,
                KnowledgeBaseMember.user_id == user_id,
            )
            .first()
        )
        if not member:
            member = KnowledgeBaseMember(
                knowledge_base_id=kb.id,
                user_id=user_id,
                role="owner",
                invited_by=user_id,
            )
            db.add(member)
            db.commit()
    except Exception:
        db.rollback()
    return {"code": 0, "message": "ok", "data": kb}

@router.get("/{kb_id}")
async def get_knowledge_base(
    request: Request,
    kb_id: int,
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    user_id = get_current_user_id(request)
    perm = KnowledgeBasePermissionService(db)
    # 确保当前用户至少有查看权限
    role = perm.ensure_permission(kb_id, user_id, "kb:view")

    service = KnowledgeBaseService(db)
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在"
        )
    data = {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "category_id": kb.category_id,
        "is_active": kb.is_active,
        "visibility": getattr(kb, "visibility", "private"),
        "role": role,
        "created_at": kb.created_at,
        "updated_at": kb.updated_at,
    }
    return {"code": 0, "message": "ok", "data": data}

@router.put("/{kb_id}")
async def update_knowledge_base(
    request: Request,
    kb_id: int,
    knowledge_base: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """更新知识库"""
    user_id = get_current_user_id(request)
    perm = KnowledgeBasePermissionService(db)
    perm.ensure_permission(kb_id, user_id, "kb:edit")
    kb_data = knowledge_base.dict(exclude_unset=True)
    if not kb_data.get("category_id") and kb_data.get("category_name"):
        name = kb_data.get("category_name").strip()
        if name:
            existing = db.query(KnowledgeBaseCategory).filter(
                KnowledgeBaseCategory.name == name,
                KnowledgeBaseCategory.is_deleted == False
            ).first()
            if existing:
                kb_data["category_id"] = existing.id
            else:
                cat_service = KnowledgeBaseCategoryService(db)
                created = cat_service.create_category({"name": name})
                kb_data["category_id"] = created["id"]
    kb_data.pop("category_name", None)
    service = KnowledgeBaseService(db)
    kb = await service.update_knowledge_base(kb_id, KnowledgeBaseUpdate.parse_obj(kb_data))
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在"
        )
    return {"code": 0, "message": "ok", "data": kb}

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    request: Request,
    kb_id: int,
    db: Session = Depends(get_db)
):
    """删除知识库"""
    user_id = get_current_user_id(request)
    perm = KnowledgeBasePermissionService(db)
    perm.ensure_permission(kb_id, user_id, "kb:delete")
    service = KnowledgeBaseService(db)
    success = await service.delete_knowledge_base(kb_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在"
        )
    return {"code": 0, "message": "ok", "data": {"id": kb_id}}


class KnowledgeBaseMemberCreate(BaseModel):
    user_id: int
    role: str = "viewer"


class KnowledgeBaseMemberUpdate(BaseModel):
    role: str


class KnowledgeBaseMemberResponse(BaseModel):
    user_id: int
    role: str
    invited_by: Optional[int] = None
    invited_at: Optional[str] = None


@router.get("/{kb_id}/members")
async def list_knowledge_base_members(
    request: Request,
    kb_id: int,
    db: Session = Depends(get_db),
):
    """
    获取知识库成员列表
    """
    user_id = get_current_user_id(request)
    perm = KnowledgeBasePermissionService(db)
    # 任何成员（viewer 及以上）都可以查看成员列表
    perm.ensure_permission(kb_id, user_id, "kb:view")

    members = (
        db.query(KnowledgeBaseMember, User)
        .join(User, KnowledgeBaseMember.user_id == User.id)
        .filter(KnowledgeBaseMember.knowledge_base_id == kb_id)
        .all()
    )
    items = [
        {
            "user_id": m.user_id,
            "username": user.username,
            "nickname": user.nickname or user.username,
            "role": m.role,
            "invited_by": m.invited_by,
            "invited_at": m.invited_at,
        }
        for m, user in members
    ]
    return {"code": 0, "message": "ok", "data": items}


@router.post("/{kb_id}/members")
async def add_knowledge_base_member(
    request: Request,
    kb_id: int,
    body: KnowledgeBaseMemberCreate = Body(...),
    db: Session = Depends(get_db),
):
    """
    邀请/添加成员
    """
    user_id = get_current_user_id(request)
    perm = KnowledgeBasePermissionService(db)
    perm.ensure_permission(kb_id, user_id, "kb:manage_members")

    # 幂等处理：已存在则更新角色
    member = (
        db.query(KnowledgeBaseMember)
        .filter(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == body.user_id,
        )
        .first()
    )
    if member:
        member.role = body.role
    else:
        member = KnowledgeBaseMember(
            knowledge_base_id=kb_id,
            user_id=body.user_id,
            role=body.role,
            invited_by=user_id,
        )
        db.add(member)
    db.commit()
    
    # 自动更新知识库的 visibility：如果有成员（除了owner），设置为 shared
    _update_kb_visibility_if_needed(db, kb_id)

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "user_id": member.user_id,
            "role": member.role,
            "invited_by": member.invited_by,
            "invited_at": member.invited_at,
        },
    }


@router.put("/{kb_id}/members/{member_user_id}")
async def update_knowledge_base_member(
    request: Request,
    kb_id: int,
    member_user_id: int,
    body: KnowledgeBaseMemberUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """
    更新成员角色
    """
    user_id = get_current_user_id(request)
    perm = KnowledgeBasePermissionService(db)
    perm.ensure_permission(kb_id, user_id, "kb:manage_members")

    member = (
        db.query(KnowledgeBaseMember)
        .filter(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == member_user_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在"
        )

    # 不允许修改 owner 为其他角色（如需转移所有权，另行设计接口）
    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能修改所有者角色"
        )

    member.role = body.role
    db.commit()

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "user_id": member.user_id,
            "role": member.role,
            "invited_by": member.invited_by,
            "invited_at": member.invited_at,
        },
    }


@router.delete("/{kb_id}/members/{member_user_id}")
async def remove_knowledge_base_member(
    request: Request,
    kb_id: int,
    member_user_id: int,
    db: Session = Depends(get_db),
):
    """
    移除成员 - 硬删除（物理删除数据库记录）
    """
    from app.core.logging import logger
    
    user_id = get_current_user_id(request)
    perm = KnowledgeBasePermissionService(db)
    perm.ensure_permission(kb_id, user_id, "kb:manage_members")

    member = (
        db.query(KnowledgeBaseMember)
        .filter(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == member_user_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在"
        )

    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除所有者"
        )

    try:
        # 硬删除：物理删除数据库记录
        logger.info(f"删除知识库成员: kb_id={kb_id}, user_id={member_user_id}, role={member.role}")
        db.delete(member)
        db.commit()
        logger.info(f"知识库成员删除成功: kb_id={kb_id}, user_id={member_user_id}")
        
        # 自动更新知识库的 visibility：如果删除后没有成员了，设置为 private
        _update_kb_visibility_if_needed(db, kb_id)
    except Exception as e:
        db.rollback()
        logger.error(f"删除知识库成员失败: kb_id={kb_id}, user_id={member_user_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除成员失败: {str(e)}"
        )

    return {"code": 0, "message": "ok", "data": {"user_id": member_user_id}}
