"""
Knowledge Base Model
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class KnowledgeBase(BaseModel):
    """知识库模型"""
    __tablename__ = "knowledge_bases"
    
    name = Column(String(255), nullable=False, comment="知识库名称")
    description = Column(Text, comment="知识库描述")
    category_id = Column(
        Integer, ForeignKey("knowledge_base_categories.id"), comment="分类ID"
    )
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, comment="用户ID（数据隔离/owner）"
    )
    is_active = Column(Boolean, default=True, comment="是否激活")
    enable_auto_tagging = Column(
        Boolean,
        default=True,
        comment="是否启用自动标签/摘要（知识库级别配置）",
    )
    enable_auto_entity_extraction = Column(
        Boolean,
        default=True,
        comment="是否启用自动实体提取（知识库级别配置）",
    )
    visibility = Column(
        String(20),
        default="private",
        nullable=False,
        comment="可见性: private/shared/public(预留)",
    )

    # 关系
    documents = relationship("Document", back_populates="knowledge_base")
    category = relationship("KnowledgeBaseCategory", back_populates="knowledge_bases")
    members = relationship("KnowledgeBaseMember", back_populates="knowledge_base", cascade="all, delete-orphan")
