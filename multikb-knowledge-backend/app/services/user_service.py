"""
User Service
用户服务
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta
import secrets

from app.models.user import User, RefreshToken, EmailVerification
from app.services.base import BaseService
from app.core.logging import logger
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import CustomException, ErrorCode
from app.config.settings import settings


class UserService(BaseService[User]):
    """用户服务"""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(
            User.username == username,
            User.is_deleted == False
        ).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(
            User.email == email,
            User.is_deleted == False
        ).first()
    
    def get_by_username_or_email(self, username_or_email: str) -> Optional[User]:
        """根据用户名或邮箱获取用户"""
        return self.db.query(User).filter(
            or_(User.username == username_or_email, User.email == username_or_email),
            User.is_deleted == False
        ).first()
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        nickname: Optional[str] = None
    ) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        if self.get_by_username(username):
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message="用户名已存在"
            )
        
        # 检查邮箱是否已存在
        if self.get_by_email(email):
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message="邮箱已被注册"
            )
        
        # 创建用户
        password_hash = get_password_hash(password)
        user_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "nickname": nickname or username,
            "status": "active",
            "email_verified": False
        }
        
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"用户注册成功: username={username}, email={email}")
        return user
    
    def update_user_info(
        self,
        user_id: int,
        nickname: Optional[str] = None,
        avatar_url: Optional[str] = None,
        phone: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[User]:
        """更新用户信息"""
        user = self.db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if not user:
            return None
        
        if nickname is not None:
            user.nickname = nickname
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if phone is not None:
            user.phone = phone
        if preferences is not None:
            import json
            user.preferences = json.dumps(preferences)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if not user:
            raise CustomException(
                code=ErrorCode.NOT_FOUND,
                message="用户不存在"
            )
        
        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message="当前密码错误"
            )
        
        # 更新密码
        new_password_hash = get_password_hash(new_password)
        user.password_hash = new_password_hash
        self.db.commit()
        
        logger.info(f"用户修改密码成功: user_id={user_id}")
        return True
    
    def check_user_locked(self, user: User) -> bool:
        """检查用户是否被锁定"""
        if user.status != "locked":
            return False
        
        if user.locked_until and user.locked_until > datetime.utcnow():
            return True
        
        # 锁定已过期，解除锁定
        user.status = "active"
        user.locked_until = None
        user.failed_login_attempts = 0
        self.db.commit()
        return False
    
    def handle_login_failure(self, user: User) -> None:
        """处理登录失败"""
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            # 锁定用户
            user.status = "locked"
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
            logger.warning(f"用户登录失败次数过多，已锁定: user_id={user.id}, attempts={user.failed_login_attempts}")
        
        self.db.commit()
    
    def handle_login_success(self, user: User, ip_address: Optional[str] = None) -> None:
        """处理登录成功"""
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.login_count += 1
        user.failed_login_attempts = 0
        user.locked_until = None
        if user.status == "locked":
            user.status = "active"
        self.db.commit()
    
    def create_email_verification(
        self,
        user_id: int,
        email: str
    ) -> EmailVerification:
        """创建邮箱验证记录"""
        # 生成6位验证码
        verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        expires_at = datetime.utcnow() + timedelta(minutes=settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES)
        
        # 创建验证记录
        verification = EmailVerification(
            user_id=user_id,
            email=email,
            verification_code=verification_code,
            expires_at=expires_at,
            is_used=False
        )
        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)
        
        # 不在日志中记录验证码，避免安全风险
        logger.info(f"创建邮箱验证码: user_id={user_id}, email={email}")
        return verification
    
    def verify_email_code(
        self,
        user_id: int,
        email: str,
        verification_code: str
    ) -> bool:
        """验证邮箱验证码"""
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user_id,
            EmailVerification.email == email,
            EmailVerification.verification_code == verification_code,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > datetime.utcnow()
        ).first()
        
        if not verification:
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message="验证码无效或已过期"
            )
        
        # 标记为已使用
        verification.is_used = True
        
        # 更新用户邮箱验证状态
        user = self.db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if user:
            user.email_verified = True
            if user.email != email:
                user.email = email
        
        self.db.commit()
        return True
