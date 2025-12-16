"""
Knowledge Base Service
"""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_category import KnowledgeBaseCategory
from app.models.knowledge_base_member import KnowledgeBaseMember
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.models.document import Document
from app.core.exceptions import CustomException, ErrorCode
from app.services.base import BaseService
from app.services.permission_service import ROLE_ACTION_MATRIX

class KnowledgeBaseService(BaseService[KnowledgeBase]):
    """知识库服务"""
    
    def __init__(self, db: Session):
        super().__init__(db, KnowledgeBase)
    
    async def get_knowledge_bases(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[KnowledgeBase]:
        """获取知识库列表"""
        return await self.get_multi(skip=skip, limit=limit)

    async def get_knowledge_bases_paginated(
        self,
        page: int = 1,
        size: int = 20,
        user_id: Optional[int] = None,
        require_permission: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """分页获取知识库列表，返回 (items(dict), total)
        包含 category_name 以便前端直接展示
        
        Args:
            page: 页码
            size: 每页大小
            user_id: 用户ID，用于过滤知识库
            require_permission: 可选，要求用户对该知识库有指定权限（如 'doc:upload'）
                               只有拥有该权限的知识库才会被返回
        """
        skip = max(page - 1, 0) * max(size, 1)
        # 构造成员关联条件：
        # - 对于指定 user_id，只关联“当前用户”的成员记录，避免因为其他成员导致重复行
        # - 对于未指定 user_id（理论上很少用），关联全部成员记录
        if user_id is not None:
            member_join_cond = and_(
                KnowledgeBaseMember.knowledge_base_id == KnowledgeBase.id,
                KnowledgeBaseMember.user_id == user_id,
            )
        else:
            member_join_cond = KnowledgeBaseMember.knowledge_base_id == KnowledgeBase.id

        # 基础查询：用户拥有的 + 作为成员被共享的
        base_query = (
            self.db.query(
                KnowledgeBase,
                KnowledgeBaseCategory.name.label("category_name"),
                KnowledgeBaseMember.role.label("member_role"),
            )
            .outerjoin(
                KnowledgeBaseCategory,
                KnowledgeBase.category_id == KnowledgeBaseCategory.id,
            )
            .outerjoin(
                KnowledgeBaseMember,
                member_join_cond,
            )
            .filter(KnowledgeBase.is_deleted == False)  # noqa: E712
        )
        if user_id is not None:
            # 仅返回：当前用户是 owner 或在成员表中有记录的知识库
            base_query = base_query.filter(
                or_(
                    KnowledgeBase.user_id == user_id,
                    KnowledgeBaseMember.user_id == user_id,
                )
            )

        # 由于存在 JOIN，计数需要对 KnowledgeBase.id 去重
        total_query = (
            self.db.query(func.count(func.distinct(KnowledgeBase.id)))
            .select_from(KnowledgeBase)
            .outerjoin(
                KnowledgeBaseMember,
                member_join_cond,
            )
            .filter(KnowledgeBase.is_deleted == False)  # noqa: E712
        )
        if user_id is not None:
            total_query = total_query.filter(
                or_(
                    KnowledgeBase.user_id == user_id,
                    KnowledgeBaseMember.user_id == user_id,
                )
            )
        total = total_query.scalar()

        # 文档数统计子查询（未删除总数 与 已完成数）
        total_sub = (
            self.db.query(
                Document.knowledge_base_id.label("kb_id"),
                func.count(Document.id).label("doc_count_total")
            )
            .filter(Document.is_deleted == False)
            .group_by(Document.knowledge_base_id)
            .subquery()
        )
        completed_sub = (
            self.db.query(
                Document.knowledge_base_id.label("kb_id"),
                func.count(Document.id).label("doc_count_completed")
            )
            .filter(Document.is_deleted == False, Document.status == 'completed')
            .group_by(Document.knowledge_base_id)
            .subquery()
        )

        # 附加计数字段后再查询
        rows_query = (
            base_query.add_columns(
                func.coalesce(total_sub.c.doc_count_total, 0).label("doc_count_total"),
                func.coalesce(
                    completed_sub.c.doc_count_completed, 0
                ).label("doc_count_completed"),
            )
            .outerjoin(total_sub, total_sub.c.kb_id == KnowledgeBase.id)
            .outerjoin(completed_sub, completed_sub.c.kb_id == KnowledgeBase.id)
            .order_by(KnowledgeBase.created_at.desc())
        )
        
        # 如果需要权限过滤，先查询所有数据，然后在应用层过滤和分页
        if require_permission:
            all_rows = rows_query.all()
            filtered_items: List[Dict[str, Any]] = []
            for kb, category_name, member_role, doc_count_total, doc_count_completed in all_rows:
                # 角色优先级：owner > admin > editor > viewer
                effective_role = member_role
                if user_id is not None and kb.user_id == user_id:
                    effective_role = "owner"
                
                # 检查该角色是否有要求的权限
                allowed_actions = ROLE_ACTION_MATRIX.get(effective_role, [])
                if require_permission not in allowed_actions:
                    # 跳过没有该权限的知识库
                    continue
                
                filtered_items.append({
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "category_id": kb.category_id,
                    "category_name": category_name,
                    "is_active": kb.is_active,
                    "visibility": getattr(kb, "visibility", "private"),
                    "role": effective_role,
                    "created_at": kb.created_at,
                    "updated_at": kb.updated_at,
                    "document_count": int(doc_count_total or 0),
                    "doc_count_total": int(doc_count_total or 0),
                    "doc_count_completed": int(doc_count_completed or 0),
                })
            
            # 重新计算过滤后的总数
            total = len(filtered_items)
            # 手动分页
            items = filtered_items[skip:skip + size]
            return items, total
        else:
            # 不需要权限过滤，正常分页查询
            rows = rows_query.offset(skip).limit(size).all()
            items: List[Dict[str, Any]] = []
            for kb, category_name, member_role, doc_count_total, doc_count_completed in rows:
                # 角色优先级：owner > admin > editor > viewer
                effective_role = member_role
                if user_id is not None and kb.user_id == user_id:
                    effective_role = "owner"

                items.append({
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "category_id": kb.category_id,
                    "category_name": category_name,
                    "is_active": kb.is_active,
                    "visibility": getattr(kb, "visibility", "private"),
                    "role": effective_role,
                    "created_at": kb.created_at,
                    "updated_at": kb.updated_at,
                    # 保持对前端兼容：document_count 沿用总数
                    "document_count": int(doc_count_total or 0),
                    # 额外提供两个口径，前端可按需展示
                    "doc_count_total": int(doc_count_total or 0),
                    "doc_count_completed": int(doc_count_completed or 0),
                })
            return items, total
    
    async def get_knowledge_base(self, kb_id: int) -> Optional[KnowledgeBase]:
        """获取知识库详情"""
        return await self.get(kb_id)
    
    async def create_knowledge_base(
        self, 
        kb_data: KnowledgeBaseCreate,
        user_id: Optional[int] = None
    ) -> KnowledgeBase:
        """创建知识库"""
        # 名称唯一性校验（在同一用户下）
        query = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.name == kb_data.name,
            KnowledgeBase.is_deleted == False
        )
        # 如果提供了user_id，添加用户过滤（支持数据隔离）
        if user_id is not None:
            query = query.filter(KnowledgeBase.user_id == user_id)
        existing = query.first()
        if existing:
            raise CustomException(code=ErrorCode.VALIDATION_ERROR, message="知识库名称已存在")
        # 排除 None/未提供的可选字段（如 category_name）
        return await self.create(kb_data.dict(exclude_none=True, exclude_unset=True))
    
    async def update_knowledge_base(
        self, 
        kb_id: int, 
        kb_data: KnowledgeBaseUpdate
    ) -> Optional[KnowledgeBase]:
        """更新知识库"""
        # 如果修改了名称，进行唯一性校验
        if kb_data.name is not None:
            conflict = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.name == kb_data.name,
                KnowledgeBase.id != kb_id,
                KnowledgeBase.is_deleted == False
            ).first()
            if conflict:
                raise CustomException(code=ErrorCode.VALIDATION_ERROR, message="知识库名称已存在")
        # 排除 None/未提供的可选字段（如 category_name）
        return await self.update(kb_id, kb_data.dict(exclude_unset=True, exclude_none=True))
    
    async def delete_knowledge_base(self, kb_id: int) -> bool:
        """删除知识库（硬删除）"""
        # 直接物理删除记录；若存在外键约束导致删除失败，将抛出异常由上层捕获
        obj = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True
