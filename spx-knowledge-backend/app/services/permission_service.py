"""
Permission and role utilities for knowledge bases.

根据知识库共享设计文档，实现基础的知识库成员/角色查询与权限校验。
"""

from typing import Optional, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_member import KnowledgeBaseMember


# 角色 -> 允许的动作集合
ROLE_ACTION_MATRIX: Dict[str, List[str]] = {
    "owner": [
        "kb:view",
        "kb:edit",
        "kb:delete",
        "kb:manage_members",
        "doc:view",
        "doc:upload",
        "doc:edit",
        "doc:delete",
        "kg:view",
        "kg:edit",
        "kg:extract",
        "kg:delete",
    ],
    "admin": [
        "kb:view",
        "kb:edit",
        "kb:manage_members",
        "doc:view",
        "doc:upload",
        "doc:edit",
        "doc:delete",
        "kg:view",
        "kg:edit",
        "kg:extract",
        "kg:delete",
    ],
    "editor": [
        "kb:view",
        "doc:view",
        "doc:upload",
        "doc:edit",
        "doc:delete",  # 简化方案：允许删除任意文档，操作记录由上层负责
        "kg:view",
        "kg:edit",
        "kg:extract",
    ],
    "viewer": [
        "kb:view",
        "doc:view",
        "kg:view",
    ],
}


class KnowledgeBasePermissionService:
    """知识库级权限服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_role_for_kb(self, kb_id: int, user_id: int) -> Optional[str]:
        """
        返回用户在某知识库下的角色: 'owner' / 'admin' / 'editor' / 'viewer' / None

        优先从 knowledge_base_members 查找；
        若不存在成员记录且用户是 knowledge_bases.user_id，则视为 owner（兼容旧数据）。
        """
        # 1) 优先成员表
        member = (
            self.db.query(KnowledgeBaseMember)
            .filter(
                KnowledgeBaseMember.knowledge_base_id == kb_id,
                KnowledgeBaseMember.user_id == user_id,
            )
            .first()
        )
        if member:
            return member.role or "viewer"

        # 2) 兼容：没有成员记录，但当前用户是 owner
        kb = (
            self.db.query(KnowledgeBase)
            .filter(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if kb and kb.user_id == user_id:
            return "owner"

        return None

    def ensure_permission(self, kb_id: int, user_id: int, action: str) -> str:
        """
        针对某个 action 做权限校验，失败抛出 HTTPException。

        返回值：通过校验后的角色字符串，方便上层继续使用。
        """
        role = self.get_user_role_for_kb(kb_id, user_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该知识库"
            )

        allowed_actions = ROLE_ACTION_MATRIX.get(role, [])
        if action not in allowed_actions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="权限不足"
            )
        return role
