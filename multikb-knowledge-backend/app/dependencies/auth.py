"""
Authentication Dependencies
"""

from typing import Optional, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import settings
from app.core.security import verify_token

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """获取当前用户 - 必须提供有效的认证令牌"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """获取可选用户（用于可选认证）"""
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    return payload


def _normalize_roles(raw_roles) -> set[str]:
    if not raw_roles:
        return set()
    if isinstance(raw_roles, str):
        return {raw_roles}
    if isinstance(raw_roles, Iterable):
        return {str(role) for role in raw_roles}
    return set()


def require_roles(required_roles: Iterable[str]):
    """动态角色校验"""

    required_set = _normalize_roles(required_roles)

    # 若未配置任何角色限制，直接放行，避免强制要求认证
    if not required_set:
        async def allow_all():
            return None

        return allow_all

    # 支持使用 "*" 表示允许任意角色访问
    if "*" in required_set:
        async def allow_any(payload=Depends(get_optional_user)):
            return payload

        return allow_any

    def dependency(payload=Depends(get_current_user)):
        roles = _normalize_roles(payload.get("roles") or payload.get("role"))
        if not roles.intersection(required_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
        return payload

    return dependency


require_observability_access = require_roles(settings.OBSERVABILITY_ALLOWED_ROLES)
