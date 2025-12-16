"""
Auth API Routes
用户认证路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.schemas.user import (
    UserRegisterRequest, RegisterResponse,
    UserLoginRequest, LoginResponse,
    TokenRefreshRequest, TokenRefreshResponse,
    UserInfo,
    PasswordResetRequest, PasswordResetConfirmRequest
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.core.logging import logger
from app.core.response import success_response
from app.core.exceptions import CustomException
from app.core.security import get_password_hash
from app.config.settings import settings

# 认证路由 - 中间件会处理认证，这里不需要设置依赖
router = APIRouter()


class LogoutRequest(BaseModel):
    """登出请求"""
    refresh_token: Optional[str] = None


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    request_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """用户注册"""
    try:
        logger.info(f"用户注册请求: username={request_data.username}, email={request_data.email}")
        
        auth_service = AuthService(db)
        user = auth_service.register(
            username=request_data.username,
            email=request_data.email,
            password=request_data.password,
            nickname=request_data.nickname
        )
        
        return RegisterResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            email_verified=user.email_verified,
            created_at=user.created_at
        )
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"用户注册错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="注册失败")


@router.post("/login", response_model=LoginResponse)
def login(
    request_data: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """用户登录"""
    try:
        logger.info(f"用户登录请求: username={request_data.username}")
        
        auth_service = AuthService(db)
        login_response, refresh_token_obj = auth_service.login(
            username_or_email=request_data.username,
            password=request_data.password,
            request=request
        )
        
        return login_response
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except Exception as e:
        logger.error(f"用户登录错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="登录失败")


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(
    request_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """刷新Token"""
    try:
        auth_service = AuthService(db)
        response, refresh_token_obj = auth_service.refresh_token(request_data.refresh_token)
        return response
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except Exception as e:
        logger.error(f"Token刷新错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token刷新失败")


@router.post("/logout")
def logout(
    request_data: Optional[LogoutRequest] = Body(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """用户登出"""
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户信息无效")
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户ID无效")
        
        refresh_token = request_data.refresh_token if request_data else None
        
        auth_service = AuthService(db)
        auth_service.logout(user_id, refresh_token)
        
        return success_response("登出成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登出错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="登出失败")


@router.get("/me", response_model=UserInfo)
def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户信息无效")
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户ID无效")
        
        user_service = UserService(db)
        user = user_service.db.query(user_service.model).filter(
            user_service.model.id == user_id,
            user_service.model.is_deleted == False
        ).first()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        
        return UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            phone=user.phone,
            status=user.status,
            email_verified=user.email_verified,
            last_login_at=user.last_login_at,
            created_at=user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取用户信息失败")


@router.post("/password/reset")
def send_password_reset_code(
    request_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """发送密码重置验证码"""
    try:
        if not settings.EMAIL_VERIFICATION_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="邮箱验证功能未启用"
            )
        
        user_service = UserService(db)
        user = user_service.get_by_email(request_data.email)
        
        if not user:
            # 为了安全，不暴露用户是否存在
            return success_response("如果邮箱存在，验证码已发送")
        
        verification = user_service.create_email_verification(
            user_id=user.id,
            email=request_data.email
        )
        
        # TODO: 实际发送邮件
        # 不在日志中记录验证码，避免安全风险
        logger.info(f"密码重置验证码已生成: user_id={user.id}, email={request_data.email}")
        
        return success_response("如果邮箱存在，验证码已发送到邮箱")
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"发送密码重置验证码错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="发送验证码失败")


@router.post("/password/reset/confirm")
def confirm_password_reset(
    request_data: PasswordResetConfirmRequest,
    db: Session = Depends(get_db)
):
    """确认密码重置"""
    try:
        if not settings.EMAIL_VERIFICATION_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="邮箱验证功能未启用"
            )
        
        user_service = UserService(db)
        user = user_service.get_by_email(request_data.email)
        
        if not user:
            # 为了安全，不暴露用户是否存在，统一返回验证失败
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码无效或已过期"
            )
        
        # 验证验证码
        user_service.verify_email_code(
            user_id=user.id,
            email=request_data.email,
            verification_code=request_data.verification_code
        )
        
        # 更新密码
        new_password_hash = get_password_hash(request_data.new_password)
        user.password_hash = new_password_hash
        
        # 撤销用户的所有RefreshToken（安全考虑）
        from app.models.user import RefreshToken
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False
        ).update({"is_revoked": True})
        
        db.commit()
        
        logger.info(f"密码重置成功: user_id={user.id}")
        return success_response("密码重置成功")
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"密码重置错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="密码重置失败")
