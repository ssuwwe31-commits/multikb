"""
User Schemas
用户认证系统Schema定义
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import re


# ==================== 认证相关 Schema ====================

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名，3-50字符，字母数字下划线")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, max_length=50, description="密码，8-50字符，包含字母和数字")
    nickname: Optional[str] = Field(None, max_length=100, description="昵称（可选）")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8 or len(v) > 50:
            raise ValueError('密码长度必须在8-50字符之间')
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含至少一个字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenRefreshRequest(BaseModel):
    """Token刷新请求"""
    refresh_token: str = Field(..., description="刷新Token")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    email: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    status: str
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(1800, description="Access Token有效期（秒）")
    user: UserInfo


class TokenRefreshResponse(BaseModel):
    """Token刷新响应"""
    access_token: str
    refresh_token: str
    expires_in: int = Field(1800, description="Access Token有效期（秒）")


class RegisterResponse(BaseModel):
    """注册响应"""
    user_id: int
    username: str
    email: str
    email_verified: bool
    created_at: datetime


# ==================== 用户管理相关 Schema ====================

class UserUpdateRequest(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好设置JSON")


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=50, description="新密码，8-50字符，包含字母和数字")
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8 or len(v) > 50:
            raise ValueError('密码长度必须在8-50字符之间')
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含至少一个字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class EmailVerifyRequest(BaseModel):
    """发送邮箱验证码请求"""
    email: EmailStr = Field(..., description="要验证的邮箱")


class EmailConfirmRequest(BaseModel):
    """验证邮箱请求"""
    email: EmailStr = Field(..., description="要验证的邮箱（必须与发送验证码时的邮箱一致）")
    verification_code: str = Field(..., min_length=6, max_length=10, description="验证码")


class EmailVerifyResponse(BaseModel):
    """邮箱验证响应"""
    email: str
    expires_in: int = Field(600, description="验证码有效期（秒）")


class EmailConfirmResponse(BaseModel):
    """邮箱确认响应"""
    email: str
    email_verified: bool


# ==================== 密码重置相关 Schema ====================

class PasswordResetRequest(BaseModel):
    """密码重置请求（发送验证码）"""
    email: EmailStr = Field(..., description="注册邮箱")


class PasswordResetConfirmRequest(BaseModel):
    """密码重置确认请求"""
    email: EmailStr = Field(..., description="注册邮箱")
    verification_code: str = Field(..., min_length=6, max_length=10, description="验证码")
    new_password: str = Field(..., min_length=8, max_length=50, description="新密码，8-50字符，包含字母和数字")
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8 or len(v) > 50:
            raise ValueError('密码长度必须在8-50字符之间')
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含至少一个字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含至少一个数字')
        return v
