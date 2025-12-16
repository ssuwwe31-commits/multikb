"""
File Utils
"""

import os
import hashlib
import mimetypes
from typing import Optional, Dict, Any
from pathlib import Path

def get_file_hash(file_path: str) -> str:
    """获取文件哈希值"""
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    except Exception as e:
        print(f"计算文件哈希错误: {e}")
        return ""

def get_file_size(file_path: str) -> int:
    """获取文件大小"""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        print(f"获取文件大小错误: {e}")
        return 0

def get_file_type(file_path: str) -> str:
    """获取文件类型"""
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"
    except Exception as e:
        print(f"获取文件类型错误: {e}")
        return "application/octet-stream"

def get_file_extension(file_path: str) -> str:
    """获取文件扩展名"""
    try:
        return Path(file_path).suffix.lower()
    except Exception as e:
        print(f"获取文件扩展名错误: {e}")
        return ""

def is_valid_file(file_path: str, allowed_extensions: list) -> bool:
    """检查文件是否有效"""
    try:
        if not os.path.exists(file_path):
            return False
        
        extension = get_file_extension(file_path)
        return extension in allowed_extensions
    except Exception as e:
        print(f"检查文件有效性错误: {e}")
        return False

def create_directory(path: str) -> bool:
    """创建目录"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录错误: {e}")
        return False

def delete_file(file_path: str) -> bool:
    """删除文件"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    except Exception as e:
        print(f"删除文件错误: {e}")
        return False
