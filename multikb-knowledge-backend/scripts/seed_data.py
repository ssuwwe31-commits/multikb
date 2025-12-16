"""
Seed Data Script
"""

import os
import sys
from sqlalchemy.orm import sessionmaker
from app.config.database import engine
from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_category import KnowledgeBaseCategory

def seed_data():
    """种子数据"""
    try:
        # 创建会话
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 创建分类
        categories = [
            KnowledgeBaseCategory(
                name="技术文档",
                description="技术相关的文档",
                sort_order=1
            ),
            KnowledgeBaseCategory(
                name="产品文档",
                description="产品相关的文档",
                sort_order=2
            ),
            KnowledgeBaseCategory(
                name="运营文档",
                description="运营相关的文档",
                sort_order=3
            )
        ]
        
        for category in categories:
            db.add(category)
        
        db.commit()
        
        # 创建知识库
        knowledge_bases = [
            KnowledgeBase(
                name="默认知识库",
                description="系统默认知识库",
                category_id=1
            ),
            KnowledgeBase(
                name="测试知识库",
                description="用于测试的知识库",
                category_id=2
            )
        ]
        
        for kb in knowledge_bases:
            db.add(kb)
        
        db.commit()
        db.close()
        
        print("种子数据创建成功")
        return True
        
    except Exception as e:
        print(f"种子数据创建失败: {e}")
        return False

if __name__ == "__main__":
    seed_data()
