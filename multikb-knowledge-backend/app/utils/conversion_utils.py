"""
Conversion Utils
"""

from typing import Any, Dict, List, Optional, Union
import json
import base64
from datetime import datetime
import pandas as pd

def dict_to_json(data: Dict[str, Any], indent: int = 2) -> str:
    """字典转JSON字符串"""
    return json.dumps(data, indent=indent, ensure_ascii=False)

def json_to_dict(json_str: str) -> Dict[str, Any]:
    """JSON字符串转字典"""
    return json.loads(json_str)

def list_to_string(data: List[str], separator: str = ",") -> str:
    """列表转字符串"""
    return separator.join(data)

def string_to_list(data: str, separator: str = ",") -> List[str]:
    """字符串转列表"""
    return data.split(separator) if data else []

def bytes_to_base64(data: bytes) -> str:
    """字节转Base64"""
    return base64.b64encode(data).decode('utf-8')

def base64_to_bytes(data: str) -> bytes:
    """Base64转字节"""
    return base64.b64decode(data)

def string_to_int(data: str, default: int = 0) -> int:
    """字符串转整数"""
    try:
        return int(data)
    except (ValueError, TypeError):
        return default

def string_to_float(data: str, default: float = 0.0) -> float:
    """字符串转浮点数"""
    try:
        return float(data)
    except (ValueError, TypeError):
        return default

def int_to_string(data: int) -> str:
    """整数转字符串"""
    return str(data)

def float_to_string(data: float, precision: int = 2) -> str:
    """浮点数转字符串"""
    return f"{data:.{precision}f}"

def datetime_to_string(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """日期时间转字符串"""
    return dt.strftime(format_str)

def string_to_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """字符串转日期时间"""
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None

def dict_to_csv(data: List[Dict[str, Any]], filename: str) -> bool:
    """字典列表转CSV文件"""
    try:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8')
        return True
    except Exception:
        return False

def csv_to_dict(filename: str) -> List[Dict[str, Any]]:
    """CSV文件转字典列表"""
    try:
        df = pd.read_csv(filename, encoding='utf-8')
        return df.to_dict('records')
    except Exception:
        return []

def convert_to_boolean(value: Any) -> bool:
    """转换为布尔值"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    if isinstance(value, (int, float)):
        return bool(value)
    return False
