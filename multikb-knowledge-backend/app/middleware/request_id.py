"""
Request ID Middleware
"""

from fastapi import Request
from fastapi.responses import Response
import uuid
import logging

logger = logging.getLogger(__name__)

async def request_id_middleware(request: Request, call_next):
    """请求ID中间件"""
    # 生成请求ID
    request_id = str(uuid.uuid4())
    
    # 将请求ID添加到请求状态中
    request.state.request_id = request_id
    
    # 处理请求
    response = await call_next(request)
    
    # 添加请求ID到响应头
    response.headers["X-Request-ID"] = request_id
    
    return response
