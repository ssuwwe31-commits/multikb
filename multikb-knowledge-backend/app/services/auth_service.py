"""
Auth Service
认证服务
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import Request

from app.models.user import User, RefreshToken
from app.services.user_service import UserService
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    verify_token,
    verify_password,
    generate_refresh_token
)
from app.core.exceptions import CustomException, ErrorCode
from app.config.settings import settings
from app.schemas.user import LoginResponse, TokenRefreshResponse, UserInfo


class AuthService:
    """认证服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
    
    def register(
        self,
        username: str,
        email: str,
        password: str,
        nickname: Optional[str] = None
    ) -> User:
        """用户注册"""
        return self.user_service.create_user(
            username=username,
            email=email,
            password=password,
            nickname=nickname
        )
    
    def login(
        self,
        username_or_email: str,
        password: str,
        request: Optional[Request] = None
    ) -> Tuple[LoginResponse, RefreshToken]:
        """用户登录"""
        # 获取用户
        user = self.user_service.get_by_username_or_email(username_or_email)
        if not user:
            raise CustomException(
                code=ErrorCode.UNAUTHORIZED,
                message="用户名或密码错误"
            )
        
        # 检查用户状态
        if self.user_service.check_user_locked(user):
            raise CustomException(
                code=ErrorCode.FORBIDDEN,
                message=f"账户已被锁定，请于 {user.locked_until} 后重试"
            )
        
        # 验证密码
        if not verify_password(password, user.password_hash):
            self.user_service.handle_login_failure(user)
            raise CustomException(
                code=ErrorCode.UNAUTHORIZED,
                message="用户名或密码错误"
            )
        
        # 登录成功
        ip_address = request.client.host if request else None
        self.user_service.handle_login_success(user, ip_address)
        
        # 生成Token
        access_token = self._create_access_token(user)
        refresh_token_obj = self._create_refresh_token(user, request)
        
        # 构建响应
        user_info = UserInfo(
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
        
        login_response = LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token_obj.token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info
        )
        
        logger.info(f"用户登录成功: user_id={user.id}, username={user.username}")
        return login_response, refresh_token_obj
    
    def refresh_token(self, refresh_token: str) -> Tuple[TokenRefreshResponse, RefreshToken]:
        """刷新Token"""
        # 查询RefreshToken
        token_obj = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token,
            RefreshToken.is_revoked == False
        ).first()
        
        if not token_obj:
            raise CustomException(
                code=ErrorCode.UNAUTHORIZED,
                message="刷新Token无效"
            )
        
        # 检查是否过期
        if token_obj.expires_at < datetime.utcnow():
            raise CustomException(
                code=ErrorCode.UNAUTHORIZED,
                message="刷新Token已过期"
            )
        
        # 获取用户
        user = self.db.query(User).filter(
            User.id == token_obj.user_id,
            User.is_deleted == False
        ).first()
        if not user or user.status != "active":
            raise CustomException(
                code=ErrorCode.UNAUTHORIZED,
                message="用户状态异常"
            )
        
        # 撤销旧Token
        token_obj.is_revoked = True
        
        # 生成新Token
        access_token = self._create_access_token(user)
        new_refresh_token_obj = self._create_refresh_token(user, None)
        
        self.db.commit()
        
        response = TokenRefreshResponse(
            access_token=access_token,
            refresh_token=new_refresh_token_obj.token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        return response, new_refresh_token_obj
    
    def logout(self, user_id: int, refresh_token: Optional[str] = None) -> bool:
        """用户登出"""
        if refresh_token:
            # 撤销指定的RefreshToken
            token_obj = self.db.query(RefreshToken).filter(
                RefreshToken.token == refresh_token,
                RefreshToken.user_id == user_id
            ).first()
            if token_obj:
                token_obj.is_revoked = True
        else:
            # 撤销用户的所有RefreshToken
            self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            ).update({"is_revoked": True})
        
        self.db.commit()
        logger.info(f"用户登出: user_id={user_id}")
        return True
    
    def _create_access_token(self, user: User) -> str:
        """创建Access Token"""
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email
        }
        return create_access_token(token_data)
    
    def _create_refresh_token(
        self,
        user: User,
        request: Optional[Request] = None
    ) -> RefreshToken:
        """创建Refresh Token"""
        token = generate_refresh_token()
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        device_info = None
        ip_address = None
        if request:
            ip_address = request.client.host
            user_agent = request.headers.get("user-agent", "")
            device_info = user_agent[:200] if user_agent else None
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
            is_revoked=False
        )
        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)
        
        return refresh_token
    
    def get_current_user_from_token(self, token: str) -> Optional[User]:
        """从Token获取当前用户"""
        payload = verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return None
        
        # 直接查询数据库，避免async问题
        user = self.db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False,
            User.status == "active"
        ).first()
        
        return user
