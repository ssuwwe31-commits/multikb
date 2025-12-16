"""
Test Utils
"""

import pytest
from app.utils.text_utils import clean_text, extract_keywords, split_text_into_chunks
from app.utils.file_utils import get_file_hash, get_file_size, get_file_type
from app.utils.validation_utils import validate_email, validate_phone, validate_url
import tempfile
import os

def test_clean_text():
    """测试文本清理"""
    text = "  这是一个  测试文本  \n\n  "
    cleaned = clean_text(text)
    assert cleaned == "这是一个 测试文本"

def test_extract_keywords():
    """测试关键词提取"""
    text = "这是一个测试文本，用于测试关键词提取功能"
    keywords = extract_keywords(text, max_keywords=5)
    assert len(keywords) <= 5
    assert "测试" in keywords

def test_split_text_into_chunks():
    """测试文本分块"""
    text = "这是一个很长的测试文本。" * 100
    chunks = split_text_into_chunks(text, chunk_size=100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)

def test_get_file_hash():
    """测试文件哈希"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        f.flush()
        
        file_hash = get_file_hash(f.name)
        assert file_hash is not None
        assert len(file_hash) == 32  # MD5 hash length
        
        os.unlink(f.name)

def test_get_file_size():
    """测试文件大小"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        f.flush()
        
        file_size = get_file_size(f.name)
        assert file_size > 0
        
        os.unlink(f.name)

def test_get_file_type():
    """测试文件类型"""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write("test content")
        f.flush()
        
        file_type = get_file_type(f.name)
        assert file_type is not None
        
        os.unlink(f.name)

def test_validate_email():
    """测试邮箱验证"""
    assert validate_email("test@example.com") == True
    assert validate_email("invalid-email") == False
    assert validate_email("") == False

def test_validate_phone():
    """测试手机号验证"""
    assert validate_phone("13800138000") == True
    assert validate_phone("12345678901") == False
    assert validate_phone("") == False

def test_validate_url():
    """测试URL验证"""
    assert validate_url("https://www.example.com") == True
    assert validate_url("http://localhost:8000") == True
    assert validate_url("invalid-url") == False
