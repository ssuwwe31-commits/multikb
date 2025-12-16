"""
Database Initialization Script
"""

import os
import sys
from sqlalchemy import create_engine
from app.config.database import Base
from app.config.settings import settings
from app.models import *

def init_database():
    """初始化数据库"""
    try:
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        print("数据库初始化成功")
        return True
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return False

def drop_database():
    """删除数据库"""
    try:
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        
        # 删除所有表
        Base.metadata.drop_all(bind=engine)
        
        print("数据库删除成功")
        return True
        
    except Exception as e:
        print(f"数据库删除失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_database()
    else:
        init_database()
