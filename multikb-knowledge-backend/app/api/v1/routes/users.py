"""
User Management API Routes
用户管理路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json

from app.schemas.user import (
    UserUpdateRequest,
    PasswordChangeRequest,
    EmailVerifyRequest, EmailVerifyResponse,
    EmailConfirmRequest, EmailConfirmResponse
)
from app.services.user_service import UserService
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.core.logging import logger
from app.core.response import success_response
from app.core.exceptions import CustomException
from app.schemas.user import UserInfo
from app.config.settings import settings
from app.models.user import User

router = APIRouter()


@router.put("/me", response_model=UserInfo)
def update_user_info(
    request_data: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    try:
        user_id = int(current_user.get("sub"))
        user_service = UserService(db)
        
        user = user_service.update_user_info(
            user_id=user_id,
            nickname=request_data.nickname,
            avatar_url=request_data.avatar_url,
            phone=request_data.phone,
            preferences=request_data.preferences
        )
        
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
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户ID无效")
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"更新用户信息错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新失败")


@router.post("/me/password")
def change_password(
    request_data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    try:
        user_id = int(current_user.get("sub"))
        user_service = UserService(db)
        
        user_service.change_password(
            user_id=user_id,
            old_password=request_data.old_password,
            new_password=request_data.new_password
        )
        
        return success_response("密码修改成功")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户ID无效")
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"修改密码错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="修改密码失败")


@router.post("/me/email/verify", response_model=EmailVerifyResponse)
def send_email_verification(
    request_data: EmailVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送邮箱验证码"""
    try:
        if not settings.EMAIL_VERIFICATION_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="邮箱验证功能未启用"
            )
        
        user_id = int(current_user.get("sub"))
        user_service = UserService(db)
        
        verification = user_service.create_email_verification(
            user_id=user_id,
            email=request_data.email
        )
        
        # TODO: 实际发送邮件（这里只记录日志）
        # 不在日志中记录验证码，避免安全风险
        logger.info(f"邮箱验证码已生成: user_id={user_id}, email={request_data.email}")
        
        return EmailVerifyResponse(
            email=request_data.email,
            expires_in=settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES * 60
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户ID无效")
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"发送邮箱验证码错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="发送验证码失败")


@router.post("/me/email/confirm", response_model=EmailConfirmResponse)
def confirm_email(
    request_data: EmailConfirmRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """验证邮箱"""
    try:
        user_id = int(current_user.get("sub"))
        user_service = UserService(db)
        
        user_service.verify_email_code(
            user_id=user_id,
            email=request_data.email,
            verification_code=request_data.verification_code
        )
        
        return EmailConfirmResponse(
            email=request_data.email,
            email_verified=True
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户ID无效")
    except CustomException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"验证邮箱错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="验证邮箱失败")


@router.get("/list")
def get_user_list(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 1000
):
    """获取用户列表（用于下拉选择）"""
    try:
        users = (
            db.query(User)
            .filter(User.is_deleted == False)
            .order_by(User.username)
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        items = [
            {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname or user.username,
                "email": user.email,
            }
            for user in users
        ]
        
        return {
            "code": 0,
            "message": "ok",
            "data": items
        }
    except Exception as e:
        logger.error(f"获取用户列表错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取用户列表失败")
