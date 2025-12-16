"""
Error Handler Middleware
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback

logger = logging.getLogger(__name__)

async def error_handler_middleware(request: Request, call_next):
    """错误处理中间件"""
    try:
        return await call_next(request)
    except HTTPException as e:
        # FastAPI HTTP异常
        logger.error(f"HTTP异常: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": True,
                "message": e.detail,
                "status_code": e.status_code
            }
        )
    except RequestValidationError as e:
        # 请求验证异常
        logger.error(f"请求验证异常: {e.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "message": "请求参数验证失败",
                "details": e.errors()
            }
        )
    except StarletteHTTPException as e:
        # Starlette HTTP异常
        logger.error(f"Starlette异常: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": True,
                "message": e.detail,
                "status_code": e.status_code
            }
        )
    except Exception as e:
        # 未处理的异常
        logger.error(f"未处理的异常: {e}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "服务器内部错误",
                "status_code": 500
            }
        )
