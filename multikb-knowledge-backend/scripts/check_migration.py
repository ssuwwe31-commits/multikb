"""
检查迁移结果
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from sqlalchemy import create_engine, text, inspect
from app.config.settings import settings

def check_migration():
    """检查迁移结果"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # 检查users表
            result = conn.execute(text("SHOW TABLES LIKE 'users'"))
            if result.fetchone():
                print("[OK] users 表已创建")
                
                # 检查字段
                result = conn.execute(text("DESCRIBE users"))
                columns = [row[0] for row in result.fetchall()]
                required_fields = ['id', 'username', 'email', 'password_hash', 'status', 'email_verified']
                for field in required_fields:
                    if field in columns:
                        print(f"  [OK] 字段 {field} 存在")
                    else:
                        print(f"  [ERROR] 字段 {field} 不存在")
            else:
                print("[ERROR] users 表不存在")
            
            # 检查refresh_tokens表
            result = conn.execute(text("SHOW TABLES LIKE 'refresh_tokens'"))
            if result.fetchone():
                print("[OK] refresh_tokens 表已创建")
            else:
                print("[ERROR] refresh_tokens 表不存在")
            
            # 检查email_verifications表
            result = conn.execute(text("SHOW TABLES LIKE 'email_verifications'"))
            if result.fetchone():
                print("[OK] email_verifications 表已创建")
            else:
                print("[ERROR] email_verifications 表不存在")
            
            # 检查knowledge_bases表的user_id字段
            result = conn.execute(text("SHOW COLUMNS FROM knowledge_bases LIKE 'user_id'"))
            if result.fetchone():
                print("[OK] knowledge_bases.user_id 字段已添加")
            else:
                print("[WARNING] knowledge_bases.user_id 字段不存在")
            
            # 检查documents表的user_id字段
            result = conn.execute(text("SHOW COLUMNS FROM documents LIKE 'user_id'"))
            if result.fetchone():
                print("[OK] documents.user_id 字段已添加")
            else:
                print("[WARNING] documents.user_id 字段不存在")
            
            # 检查qa_sessions表的user_id字段类型
            result = conn.execute(text("SHOW COLUMNS FROM qa_sessions WHERE Field = 'user_id'"))
            user_id_info = result.fetchone()
            if user_id_info:
                print(f"[OK] qa_sessions.user_id 字段存在，类型: {user_id_info[1]}")
                if 'INT' not in user_id_info[1].upper():
                    print(f"  [WARNING] user_id 类型为 {user_id_info[1]}，可能需要转换为 INT")
            else:
                print("[WARNING] qa_sessions.user_id 字段不存在")
            
            # 检查外键约束
            result = conn.execute(text("""
                SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                AND REFERENCED_TABLE_NAME = 'users'
            """))
            foreign_keys = result.fetchall()
            if foreign_keys:
                print(f"\n[OK] 找到 {len(foreign_keys)} 个指向 users 表的外键:")
                for fk in foreign_keys:
                    print(f"  - {fk[1]}.{fk[2]} -> {fk[3]}.{fk[4]} ({fk[0]})")
            else:
                print("\n[WARNING] 未找到指向 users 表的外键")
        
        print("\n检查完成！")
        return True
        
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_migration()
