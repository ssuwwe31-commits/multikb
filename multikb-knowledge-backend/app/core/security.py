"""
Security Module
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import bcrypt
from app.config.settings import settings

# 密码加密上下文
# 使用bcrypt，设置明确的rounds以避免版本兼容性问题
# bcrypt版本警告可以忽略，不影响功能
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,  # 明确设置rounds，避免版本兼容性问题
    deprecated="auto"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码
    
    使用与get_password_hash相同的处理方式：
    1. 先尝试直接验证（兼容旧密码，长度<=72字节）
    2. 如果失败且密码>72字节，尝试SHA256哈希后验证
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        
        # 方式1：如果密码<=72字节，先尝试直接验证
        if len(password_bytes) <= 72:
            # 使用bcrypt直接验证bytes
            if bcrypt.checkpw(password_bytes, hashed_password_bytes):
                return True
        
        # 方式2：如果密码>72字节，使用SHA256哈希后验证
        if len(password_bytes) > 72:
            password_hash = hashlib.sha256(password_bytes).hexdigest()
            password_hash_bytes = password_hash.encode('utf-8')
            # 确保不超过72字节
            if len(password_hash_bytes) > 72:
                password_hash_bytes = password_hash_bytes[:72]
            if bcrypt.checkpw(password_hash_bytes, hashed_password_bytes):
                return True
        
        # 如果都失败，返回False
        return False
    except Exception as e:
        # 如果验证失败，可能是密码格式问题
        from app.core.logging import logger
        logger.error(f"密码验证错误: {e}")
        return False

def get_password_hash(password: str) -> str:
    """获取密码哈希
    
    bcrypt最多支持72字节的密码，如果密码超过72字节，先使用SHA256哈希再bcrypt
    这样可以支持任意长度的密码，同时保持安全性
    
    处理方式：
    1. 如果密码<=72字节，直接bcrypt
    2. 如果密码>72字节，先SHA256哈希（得到64字节的hex字符串），然后bcrypt
    """
    password_bytes = password.encode('utf-8')
    password_byte_len = len(password_bytes)
    
    # bcrypt限制：最多72字节（注意：是字节数，不是字符数）
    if password_byte_len > 72:
        # 先使用SHA256哈希，得到64字节的十六进制字符串（小于72字节）
        password_hash = hashlib.sha256(password_bytes).hexdigest()
        # SHA256的hexdigest是64个字符（64字节），确保不超过72字节
        # 直接使用bytes进行bcrypt，避免字符串编码问题
        password_for_bcrypt_bytes = password_hash.encode('utf-8')
    else:
        password_for_bcrypt_bytes = password_bytes
    
    # 最终检查：确保不超过72字节
    if len(password_for_bcrypt_bytes) > 72:
        # 如果仍然超过72字节（理论上不应该发生），截断到72字节
        password_for_bcrypt_bytes = password_for_bcrypt_bytes[:72]
    
    try:
        # 使用bcrypt直接哈希bytes，避免字符串编码问题
        # bcrypt.hashpw接受bytes，返回bytes，然后解码为字符串
        salt = bcrypt.gensalt(rounds=12)
        hashed_bytes = bcrypt.hashpw(password_for_bcrypt_bytes, salt)
        return hashed_bytes.decode('utf-8')
    except Exception as e:
        from app.core.logging import logger
        logger.error(
            f"密码哈希错误: {e}, "
            f"原始密码长度: {password_byte_len} 字节, "
            f"处理后长度: {len(password_for_bcrypt_bytes)} 字节"
        )
        raise

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """验证令牌"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"],
            options={"verify_exp": True}  # 确保验证过期时间
        )
        return payload
    except JWTError:
        return None


def generate_refresh_token() -> str:
    """生成刷新Token（随机字符串）"""
    import secrets
    return secrets.token_urlsafe(32)
