"""
Response Module
"""

from typing import Any, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: bool = True
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ValidationErrorResponse(BaseModel):
    """验证错误响应"""
    success: bool = False
    error: bool = True
    message: str = "请求参数验证失败"
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

def success_response(message_or_data: Any, data: Any = None):
    """
    创建成功响应（返回字典，兼容 FastAPI）
    
    用法:
    - success_response("消息", data_dict)  # 传递消息和数据
    - success_response(data_dict)          # 只传递数据，消息默认为"success"
    """
    if data is None and isinstance(message_or_data, (dict, list)):
        # 只传递了数据，没有消息
        return {
            "success": True,
            "message": "success",
            "data": message_or_data,
            "timestamp": datetime.now().isoformat()
        }
    else:
        # 传递了消息和数据
        return {
            "success": True,
            "message": message_or_data,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

def error_response(message: str, details: Dict[str, Any] = None):
    """创建错误响应（返回字典，兼容 FastAPI）"""
    return {
        "success": False,
        "error": True,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }

def validation_error_response(details: Dict[str, Any]) -> ValidationErrorResponse:
    """创建验证错误响应"""
    return ValidationErrorResponse(details=details)
