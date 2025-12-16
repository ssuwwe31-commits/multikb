"""
Test Knowledge Base Service
"""

import pytest
from app.services.knowledge_base_service import KnowledgeBaseService
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate

def test_create_knowledge_base(db_session):
    """测试创建知识库"""
    service = KnowledgeBaseService(db_session)
    
    kb_data = KnowledgeBaseCreate(
        name="测试知识库",
        description="这是一个测试知识库"
    )
    
    kb = service.create_knowledge_base(kb_data)
    
    assert kb.name == "测试知识库"
    assert kb.description == "这是一个测试知识库"
    assert kb.is_active == True

def test_get_knowledge_base(db_session):
    """测试获取知识库"""
    service = KnowledgeBaseService(db_session)
    
    # 先创建一个知识库
    kb_data = KnowledgeBaseCreate(name="测试知识库")
    kb = service.create_knowledge_base(kb_data)
    
    # 获取知识库
    retrieved_kb = service.get_knowledge_base(kb.id)
    
    assert retrieved_kb is not None
    assert retrieved_kb.name == "测试知识库"

def test_update_knowledge_base(db_session):
    """测试更新知识库"""
    service = KnowledgeBaseService(db_session)
    
    # 先创建一个知识库
    kb_data = KnowledgeBaseCreate(name="测试知识库")
    kb = service.create_knowledge_base(kb_data)
    
    # 更新知识库
    update_data = KnowledgeBaseUpdate(name="更新后的知识库")
    updated_kb = service.update_knowledge_base(kb.id, update_data)
    
    assert updated_kb is not None
    assert updated_kb.name == "更新后的知识库"

def test_delete_knowledge_base(db_session):
    """测试删除知识库"""
    service = KnowledgeBaseService(db_session)
    
    # 先创建一个知识库
    kb_data = KnowledgeBaseCreate(name="测试知识库")
    kb = service.create_knowledge_base(kb_data)
    
    # 删除知识库
    success = service.delete_knowledge_base(kb.id)
    
    assert success == True
    
    # 验证知识库已被软删除
    deleted_kb = service.get_knowledge_base(kb.id)
    assert deleted_kb is None
