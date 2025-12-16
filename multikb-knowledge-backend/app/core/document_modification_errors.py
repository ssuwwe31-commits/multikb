"""
Document Modification Error Codes
根据文档修改功能设计实现错误码系统
"""

from enum import Enum
from typing import Dict, Any

class DocumentModificationErrorCode(Enum):
    """文档修改错误码 - 严格按照设计文档实现"""
    
    # 内容验证错误 (7001-7003)
    CONTENT_TOO_LONG = 7001
    CONTENT_FORMAT_ERROR = 7002
    CONTENT_ENCODING_ERROR = 7003
    
    # 修改处理错误 (7004-7006)
    CHUNK_NOT_FOUND = 7004
    PERMISSION_DENIED = 7005
    VERSION_CONFLICT = 7006
    
    # 向量化错误 (7007-7008)
    VECTORIZATION_FAILED = 7007
    MODEL_UNAVAILABLE = 7008
    
    # 索引更新错误 (7009-7010)
    INDEX_UPDATE_FAILED = 7009
    CACHE_UPDATE_FAILED = 7010
    
    # 版本管理错误 (7011-7015)
    VERSION_NOT_FOUND = 7011
    VERSION_CREATE_FAILED = 7012
    VERSION_ROLLBACK_FAILED = 7013
    VERSION_COMPARE_FAILED = 7014
    VERSION_DELETE_FAILED = 7015
    
    # 一致性检查错误 (7016-7020)
    CONSISTENCY_CHECK_FAILED = 7016
    CONSISTENCY_REPAIR_FAILED = 7017
    DATA_SYNC_FAILED = 7018
    STATE_ROLLBACK_FAILED = 7019
    OPERATION_CONFLICT = 7020

class DocumentModificationErrorMessages:
    """文档修改错误消息 - 根据设计文档实现"""
    
    ERROR_MESSAGES = {
        # 内容验证错误
        DocumentModificationErrorCode.CONTENT_TOO_LONG: "内容长度超过限制，请缩短内容",
        DocumentModificationErrorCode.CONTENT_FORMAT_ERROR: "内容格式不正确，请检查格式",
        DocumentModificationErrorCode.CONTENT_ENCODING_ERROR: "内容编码错误，请检查字符编码",
        
        # 修改处理错误
        DocumentModificationErrorCode.CHUNK_NOT_FOUND: "块不存在，请检查块ID",
        DocumentModificationErrorCode.PERMISSION_DENIED: "权限不足，无法执行修改操作",
        DocumentModificationErrorCode.VERSION_CONFLICT: "版本冲突，请刷新后重试",
        
        # 向量化错误
        DocumentModificationErrorCode.VECTORIZATION_FAILED: "向量化失败，请检查Ollama服务状态",
        DocumentModificationErrorCode.MODEL_UNAVAILABLE: "embedding模型不可用，请检查模型配置",
        
        # 索引更新错误
        DocumentModificationErrorCode.INDEX_UPDATE_FAILED: "索引更新失败，请检查OpenSearch服务",
        DocumentModificationErrorCode.CACHE_UPDATE_FAILED: "缓存更新失败，请检查Redis服务",
        
        # 版本管理错误
        DocumentModificationErrorCode.VERSION_NOT_FOUND: "版本不存在，请检查版本号",
        DocumentModificationErrorCode.VERSION_CREATE_FAILED: "版本创建失败，请重试",
        DocumentModificationErrorCode.VERSION_ROLLBACK_FAILED: "版本回退失败，请重试",
        DocumentModificationErrorCode.VERSION_COMPARE_FAILED: "版本比较失败，请重试",
        DocumentModificationErrorCode.VERSION_DELETE_FAILED: "版本删除失败，请重试",
        
        # 一致性检查错误
        DocumentModificationErrorCode.CONSISTENCY_CHECK_FAILED: "一致性检查失败，请重试",
        DocumentModificationErrorCode.CONSISTENCY_REPAIR_FAILED: "一致性修复失败，请重试",
        DocumentModificationErrorCode.DATA_SYNC_FAILED: "数据同步失败，请重试",
        DocumentModificationErrorCode.STATE_ROLLBACK_FAILED: "状态回滚失败，请重试",
        DocumentModificationErrorCode.OPERATION_CONFLICT: "操作冲突，请等待当前操作完成"
    }
    
    @classmethod
    def get_error_message(cls, error_code: DocumentModificationErrorCode) -> str:
        """获取错误消息"""
        return cls.ERROR_MESSAGES.get(error_code, "未知错误")

class DocumentModificationErrorResponse:
    """文档修改错误响应 - 根据设计文档实现"""
    
    @staticmethod
    def create_error_response(
        error_code: DocumentModificationErrorCode,
        detail: str = None,
        additional_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """创建错误响应"""
        message = DocumentModificationErrorMessages.get_error_message(error_code)
        
        response = {
            "status": "error",
            "error_code": error_code.value,
            "error_message": message,
            "detail": detail or message,
            "timestamp": "2024-01-01T10:00:00Z"  # TODO: 使用实际时间戳
        }
        
        if additional_data:
            response["additional_data"] = additional_data
        
        return response
    
    @staticmethod
    def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """创建成功响应"""
        return {
            "status": "success",
            "data": data,
            "timestamp": "2024-01-01T10:00:00Z"  # TODO: 使用实际时间戳
        }
