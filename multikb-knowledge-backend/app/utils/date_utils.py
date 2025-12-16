"""
Date Utils
"""

from datetime import datetime, timedelta
from typing import Optional, Union
import pytz

def get_current_time() -> datetime:
    """获取当前时间"""
    return datetime.now(pytz.UTC)

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    if dt is None:
        return ""
    return dt.strftime(format_str)

def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """解析日期时间字符串"""
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None

def add_days(dt: datetime, days: int) -> datetime:
    """添加天数"""
    return dt + timedelta(days=days)

def add_hours(dt: datetime, hours: int) -> datetime:
    """添加小时"""
    return dt + timedelta(hours=hours)

def add_minutes(dt: datetime, minutes: int) -> datetime:
    """添加分钟"""
    return dt + timedelta(minutes=minutes)

def get_time_diff(start_time: datetime, end_time: datetime) -> timedelta:
    """获取时间差"""
    return end_time - start_time

def is_expired(dt: datetime, expire_hours: int = 24) -> bool:
    """检查是否过期"""
    return datetime.now() > dt + timedelta(hours=expire_hours)

def get_timestamp() -> int:
    """获取时间戳"""
    return int(datetime.now().timestamp())

def timestamp_to_datetime(timestamp: int) -> datetime:
    """时间戳转日期时间"""
    return datetime.fromtimestamp(timestamp)
