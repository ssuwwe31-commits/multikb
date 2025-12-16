"""
Test Document Service
"""

import pytest
from app.services.document_service import DocumentService
from app.schemas.document import DocumentCreate, DocumentUpdate
from fastapi import UploadFile
from io import BytesIO

def test_create_document(db_session):
    """测试创建文档"""
    service = DocumentService(db_session)
    
    doc_data = DocumentCreate(
        original_filename="test.pdf",
        file_type="application/pdf",
        file_size=1024,
        knowledge_base_id=1
    )
    
    doc = service.create_document(doc_data)
    
    assert doc.original_filename == "test.pdf"
    assert doc.file_type == "application/pdf"
    assert doc.file_size == 1024
    assert doc.knowledge_base_id == 1

def test_get_document(db_session):
    """测试获取文档"""
    service = DocumentService(db_session)
    
    # 先创建一个文档
    doc_data = DocumentCreate(
        original_filename="test.pdf",
        knowledge_base_id=1
    )
    doc = service.create_document(doc_data)
    
    # 获取文档
    retrieved_doc = service.get_document(doc.id)
    
    assert retrieved_doc is not None
    assert retrieved_doc.original_filename == "test.pdf"

def test_update_document(db_session):
    """测试更新文档"""
    service = DocumentService(db_session)
    
    # 先创建一个文档
    doc_data = DocumentCreate(
        original_filename="test.pdf",
        knowledge_base_id=1
    )
    doc = service.create_document(doc_data)
    
    # 更新文档
    update_data = DocumentUpdate(
        original_filename="updated.pdf"
    )
    updated_doc = service.update_document(doc.id, update_data)
    
    assert updated_doc is not None
    assert updated_doc.original_filename == "updated.pdf"

def test_delete_document(db_session):
    """测试删除文档"""
    service = DocumentService(db_session)
    
    # 先创建一个文档
    doc_data = DocumentCreate(
        original_filename="test.pdf",
        knowledge_base_id=1
    )
    doc = service.create_document(doc_data)
    
    # 删除文档
    success = service.delete_document(doc.id)
    
    assert success == True
    
    # 验证文档已被软删除
    deleted_doc = service.get_document(doc.id)
    assert deleted_doc is None
