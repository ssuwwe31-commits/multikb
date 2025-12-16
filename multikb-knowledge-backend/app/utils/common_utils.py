"""
Common Utils
"""

import os
import sys
import random
import string
from typing import Any, Dict, List, Optional, Union
import uuid

def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())

def generate_random_string(length: int = 8) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_random_number(min_val: int = 1000, max_val: int = 9999) -> int:
    """生成随机数字"""
    return random.randint(min_val, max_val)

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """安全获取字典值"""
    try:
        return data.get(key, default)
    except (AttributeError, TypeError):
        return default

def safe_set(data: Dict[str, Any], key: str, value: Any) -> bool:
    """安全设置字典值"""
    try:
        data[key] = value
        return True
    except (AttributeError, TypeError):
        return False

def chunk_list(data: List[Any], chunk_size: int) -> List[List[Any]]:
    """将列表分块"""
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

def flatten_list(data: List[List[Any]]) -> List[Any]:
    """展平嵌套列表"""
    result = []
    for item in data:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result

def remove_duplicates(data: List[Any]) -> List[Any]:
    """移除重复项"""
    return list(dict.fromkeys(data))

def get_environment_variable(key: str, default: str = "") -> str:
    """获取环境变量"""
    return os.getenv(key, default)

def is_development() -> bool:
    """检查是否为开发环境"""
    return get_environment_variable("ENVIRONMENT", "development").lower() == "development"

def is_production() -> bool:
    """检查是否为生产环境"""
    return get_environment_variable("ENVIRONMENT", "development").lower() == "production"

def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    return {
        "python_version": sys.version,
        "platform": sys.platform,
        "architecture": sys.maxsize > 2**32 and "64bit" or "32bit"
    }

def format_bytes(bytes_size: int) -> str:
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

def format_number(number: int) -> str:
    """格式化数字"""
    if number < 1000:
        return str(number)
    elif number < 1000000:
        return f"{number/1000:.1f}K"
    elif number < 1000000000:
        return f"{number/1000000:.1f}M"
    else:
        return f"{number/1000000000:.1f}B"
