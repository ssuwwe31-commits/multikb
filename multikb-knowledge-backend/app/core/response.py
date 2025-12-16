"""
Response Module
"""

from typing import Any, Optional, Dict
from datetime import datetime
from pydantic import BaseModel

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str
    data: Optional[Any] = None
    timestamp: datetime = datetime.now()

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: bool = True
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()

class ValidationErrorResponse(BaseModel):
    """验证错误响应"""
    success: bool = False
    error: bool = True
    message: str = "请求参数验证失败"
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()

def success_response(message: str, data: Any = None) -> SuccessResponse:
    """创建成功响应"""
    return SuccessResponse(message=message, data=data)

def error_response(message: str, details: Dict[str, Any] = None) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(message=message, details=details)

def validation_error_response(details: Dict[str, Any]) -> ValidationErrorResponse:
    """创建验证错误响应"""
    return ValidationErrorResponse(details=details)
