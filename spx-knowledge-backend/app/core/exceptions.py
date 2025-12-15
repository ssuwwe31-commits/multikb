"""
Exception Handlers
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)

class ErrorCode:
    """错误代码定义 - 根据设计文档实现"""
    # 通用错误
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # 文件验证错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    DOCUMENT_ALREADY_EXISTS = "DOCUMENT_ALREADY_EXISTS"
    
    # 解析处理错误
    DOCUMENT_PARSING_FAILED = "DOCUMENT_PARSING_FAILED"
    IMAGE_PROCESSING_FAILED = "IMAGE_PROCESSING_FAILED"
    
    # 向量化错误
    VECTOR_GENERATION_FAILED = "VECTOR_GENERATION_FAILED"
    VECTOR_NOT_FOUND = "VECTOR_NOT_FOUND"
    
    # Ollama错误
    OLLAMA_API_FAILED = "OLLAMA_API_FAILED"
    
    # OpenSearch错误
    OPENSEARCH_CONNECTION_FAILED = "OPENSEARCH_CONNECTION_FAILED"
    OPENSEARCH_INDEX_FAILED = "OPENSEARCH_INDEX_FAILED"
    OPENSEARCH_SEARCH_FAILED = "OPENSEARCH_SEARCH_FAILED"
    
    # MinIO错误
    MINIO_UPLOAD_FAILED = "MINIO_UPLOAD_FAILED"
    MINIO_DOWNLOAD_FAILED = "MINIO_DOWNLOAD_FAILED"
    
    # 搜索错误
    SEARCH_FAILED = "SEARCH_FAILED"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"

class CustomException(Exception):
    """自定义异常类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)

def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP异常处理器"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求验证异常处理器"""
        # 记录详细的验证错误信息
        error_details = exc.errors()
        logger.error(
            f"请求参数验证失败: {request.method} {request.url.path} "
            f"查询参数: {dict(request.query_params)} "
            f"错误详情: {error_details}"
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "message": "请求参数验证失败",
                "details": error_details
            }
        )
    
    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        """业务自定义异常处理器 - 返回200并用code区分，便于前端统一处理"""
        return JSONResponse(
            status_code=200,
            content={
                "code": 400,
                "message": exc.message,
                "error_code": exc.code
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Starlette异常处理器"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理器"""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "服务器内部错误",
                "status_code": 500
            }
        )
