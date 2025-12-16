"""
Test Models
"""

import pytest
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.chunk import DocumentChunk
from datetime import datetime

def test_knowledge_base_model():
    """测试知识库模型"""
    kb = KnowledgeBase(
        name="测试知识库",
        description="这是一个测试知识库",
        category_id=1,
        is_active=True
    )
    
    assert kb.name == "测试知识库"
    assert kb.description == "这是一个测试知识库"
    assert kb.category_id == 1
    assert kb.is_active == True
    assert kb.is_deleted == False

def test_document_model():
    """测试文档模型"""
    doc = Document(
        original_filename="test.pdf",
        file_type="application/pdf",
        file_size=1024,
        file_hash="abc123",
        file_path="/path/to/file",
        knowledge_base_id=1,
        status="uploaded",
        processing_progress=0.0
    )
    
    assert doc.original_filename == "test.pdf"
    assert doc.file_type == "application/pdf"
    assert doc.file_size == 1024
    assert doc.file_hash == "abc123"
    assert doc.file_path == "/path/to/file"
    assert doc.knowledge_base_id == 1
    assert doc.status == "uploaded"
    assert doc.processing_progress == 0.0
    assert doc.is_deleted == False

def test_document_chunk_model():
    """测试文档分块模型"""
    chunk = DocumentChunk(
        document_id=1,
        content="这是一个测试分块",
        chunk_index=0,
        chunk_type="text",
        meta='{"key": "value"}'
    )
    
    assert chunk.document_id == 1
    assert chunk.content == "这是一个测试分块"
    assert chunk.chunk_index == 0
    assert chunk.chunk_type == "text"
    assert chunk.meta == '{"key": "value"}'
    assert chunk.is_deleted == False
