"""
Validators Module
"""

from typing import Any, Optional
import re
from fastapi import HTTPException, status

def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """验证密码强度"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

def validate_file_type(filename: str, allowed_types: list) -> bool:
    """验证文件类型"""
    if not filename:
        return False
    
    file_extension = filename.lower().split('.')[-1]
    return f".{file_extension}" in allowed_types

def validate_file_size(file_size: int, max_size: int) -> bool:
    """验证文件大小"""
    return file_size <= max_size

def validate_knowledge_base_name(name: str) -> bool:
    """验证知识库名称"""
    if not name or len(name.strip()) == 0:
        return False
    if len(name) > 255:
        return False
    return True

def validate_document_title(title: str) -> bool:
    """验证文档标题"""
    if not title or len(title.strip()) == 0:
        return False
    if len(title) > 500:
        return False
    return True

def validate_search_query(query: str) -> bool:
    """验证搜索查询"""
    if not query or len(query.strip()) == 0:
        return False
    if len(query) > 1000:
        return False
    return True
