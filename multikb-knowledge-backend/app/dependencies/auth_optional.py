"""
可选认证依赖 - 用于不需要强制认证的路由
"""

from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_token

security = HTTPBearer(auto_error=False)

def skip_auth():
    """跳过认证的依赖函数"""
    return None
