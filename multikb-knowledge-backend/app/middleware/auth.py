"""
Authentication Middleware
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.security import verify_token
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

def create_error_response(status_code: int, detail: str, request: Request) -> JSONResponse:
    """创建包含 CORS 头的错误响应"""
    response = JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else {}
    )
    # 添加 CORS 头（如果请求中有 Origin）
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

async def auth_middleware(request: Request, call_next):
    """认证中间件 - 所有/api路径都需要认证，除了认证相关的接口"""
    # 跳过 OPTIONS 预检请求（CORS 预检）
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # 跳过认证的路径
    skip_paths = ["/", "/health", "/docs", "/redoc", "/openapi.json"]
    
    # 跳过认证相关的API路径
    path = request.url.path
    skip_auth_paths = [
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/auth/password/reset",
        "/api/auth/password/reset/confirm"
    ]
    
    # 检查是否在跳过列表中
    if path in skip_paths:
        return await call_next(request)
    
    # 检查是否是认证相关的API路径（精确匹配）
    if path in skip_auth_paths:
        return await call_next(request)
    
    
    # 对于所有其他/api路径，需要认证
    if path.startswith("/api/"):
        # 获取Authorization头或查询参数中的token（用于图片等资源请求）
        authorization = request.headers.get("Authorization")
        token = None
        
        if authorization:
            # 检查Bearer格式
            if not authorization.startswith("Bearer "):
                return create_error_response(
                    status.HTTP_401_UNAUTHORIZED,
                    "认证令牌格式错误",
                    request
                )
            # 提取令牌
            token = authorization.split(" ")[1]
        else:
            # 尝试从查询参数获取token（用于图片等资源请求）
            token = request.query_params.get("token")
        
        if not token:
            return create_error_response(
                status.HTTP_401_UNAUTHORIZED,
                "缺少认证令牌",
                request
            )
        
        # 验证令牌
        payload = verify_token(token)
        if not payload:
            return create_error_response(
                status.HTTP_401_UNAUTHORIZED,
                "认证令牌无效或已过期",
                request
            )
        
        # 将用户信息添加到请求中
        request.state.user = payload
    
    return await call_next(request)
