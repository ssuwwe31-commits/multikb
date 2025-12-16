"""
Validation Utils
"""

import re
from typing import Any, Optional, List, Dict
from fastapi import HTTPException, status

def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_url(url: str) -> bool:
    """验证URL格式"""
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return bool(re.match(pattern, url))

def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """验证文件扩展名"""
    if not filename:
        return False
    
    file_extension = filename.lower().split('.')[-1]
    return f".{file_extension}" in allowed_extensions

def validate_file_size(file_size: int, max_size: int) -> bool:
    """验证文件大小"""
    return file_size <= max_size

def validate_string_length(text: str, min_length: int = 0, max_length: int = 1000) -> bool:
    """验证字符串长度"""
    if text is None:
        return min_length == 0
    
    length = len(text)
    return min_length <= length <= max_length

def validate_integer_range(value: int, min_value: int = 0, max_value: int = 1000000) -> bool:
    """验证整数范围"""
    return min_value <= value <= max_value

def validate_float_range(value: float, min_value: float = 0.0, max_value: float = 1000000.0) -> bool:
    """验证浮点数范围"""
    return min_value <= value <= max_value

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """验证必需字段"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    return missing_fields

def validate_data_types(data: Dict[str, Any], field_types: Dict[str, type]) -> List[str]:
    """验证数据类型"""
    invalid_fields = []
    for field, expected_type in field_types.items():
        if field in data and not isinstance(data[field], expected_type):
            invalid_fields.append(field)
    return invalid_fields

def raise_validation_error(message: str, details: Optional[Dict[str, Any]] = None):
    """抛出验证错误"""
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": "验证失败",
            "message": message,
            "details": details or {}
        }
    )
