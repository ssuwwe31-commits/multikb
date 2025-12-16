"""
Data Migration Script
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.config.database import Base
from app.config.settings import settings

def migrate_database():
    """数据库迁移"""
    try:
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        
        # 执行迁移SQL
        migration_sql = """
        -- 添加新字段的示例
        -- ALTER TABLE knowledge_bases ADD COLUMN new_field VARCHAR(255);
        
        -- 创建新索引的示例
        -- CREATE INDEX idx_documents_status ON documents(status);
        
        -- 更新数据的示例
        -- UPDATE documents SET status = 'completed' WHERE status = 'processed';
        """
        
        with engine.connect() as conn:
            conn.execute(text(migration_sql))
            conn.commit()
        
        print("数据库迁移成功")
        return True
        
    except Exception as e:
        print(f"数据库迁移失败: {e}")
        return False

if __name__ == "__main__":
    migrate_database()
