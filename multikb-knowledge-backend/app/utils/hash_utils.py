"""
Hash Utils
"""

import hashlib
import secrets
from typing import Optional

def generate_hash(data: str, algorithm: str = "md5") -> str:
    """生成哈希值"""
    if algorithm == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    else:
        raise ValueError(f"不支持的哈希算法: {algorithm}")

def generate_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """生成文件哈希值"""
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()

def generate_random_string(length: int = 32) -> str:
    """生成随机字符串"""
    return secrets.token_urlsafe(length)

def generate_random_hex(length: int = 32) -> str:
    """生成随机十六进制字符串"""
    return secrets.token_hex(length)

def verify_hash(data: str, hash_value: str, algorithm: str = "md5") -> bool:
    """验证哈希值"""
    return generate_hash(data, algorithm) == hash_value

def generate_password_hash(password: str) -> str:
    """生成密码哈希"""
    return generate_hash(password, "sha256")

def verify_password_hash(password: str, hash_value: str) -> bool:
    """验证密码哈希"""
    return verify_hash(password, hash_value, "sha256")
