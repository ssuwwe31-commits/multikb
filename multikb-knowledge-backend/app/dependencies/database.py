"""
Database Dependencies
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from app.config.database import SessionLocal

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
