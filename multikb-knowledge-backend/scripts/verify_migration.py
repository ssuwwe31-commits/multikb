"""
详细验证迁移结果
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from sqlalchemy import create_engine, text
from app.config.settings import settings

def verify_migration():
    """详细验证迁移结果"""
    print("=" * 60)
    print("数据库迁移验证")
    print("=" * 60)
    print()
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # 1. 检查 users 表
            print("1. 检查 users 表...")
            result = conn.execute(text("SHOW TABLES LIKE 'users'"))
            if result.fetchone():
                print("   [OK] users 表存在")
                
                # 检查所有字段
                result = conn.execute(text("DESCRIBE users"))
                columns = {row[0]: row[1] for row in result.fetchall()}
                
                required_fields = {
                    'id': 'int',
                    'username': 'varchar',
                    'email': 'varchar',
                    'password_hash': 'varchar',
                    'nickname': 'varchar',
                    'avatar_url': 'varchar',
                    'phone': 'varchar',
                    'status': 'varchar',
                    'email_verified': 'tinyint',
                    'last_login_at': 'datetime',
                    'last_login_ip': 'varchar',
                    'login_count': 'int',
                    'failed_login_attempts': 'int',
                    'locked_until': 'datetime',
                    'preferences': 'text',
                    'created_at': 'datetime',
                    'updated_at': 'datetime',
                    'is_deleted': 'tinyint'
                }
                
                for field, expected_type in required_fields.items():
                    if field in columns:
                        actual_type = columns[field].lower()
                        if expected_type in actual_type:
                            print(f"   [OK] 字段 {field:25} 存在，类型: {columns[field]}")
                        else:
                            print(f"   [WARNING] 字段 {field:25} 存在，但类型可能不匹配: {columns[field]}")
                    else:
                        print(f"   [ERROR] 字段 {field:25} 不存在")
                
                # 检查索引
                result = conn.execute(text("SHOW INDEXES FROM users"))
                indexes = [row[2] for row in result.fetchall()]
                required_indexes = ['uk_user_username', 'uk_user_email', 'idx_user_status', 'idx_user_email_verified']
                for idx in required_indexes:
                    if idx in indexes:
                        print(f"   [OK] 索引 {idx} 存在")
                    else:
                        print(f"   [WARNING] 索引 {idx} 不存在")
            else:
                print("   [ERROR] users 表不存在")
            
            print()
            
            # 2. 检查 refresh_tokens 表
            print("2. 检查 refresh_tokens 表...")
            result = conn.execute(text("SHOW TABLES LIKE 'refresh_tokens'"))
            if result.fetchone():
                print("   [OK] refresh_tokens 表存在")
                
                result = conn.execute(text("DESCRIBE refresh_tokens"))
                columns = {row[0]: row[1] for row in result.fetchall()}
                
                required_fields = {
                    'id': 'int',
                    'user_id': 'int',
                    'token': 'varchar',
                    'expires_at': 'datetime',
                    'device_info': 'varchar',
                    'ip_address': 'varchar',
                    'is_revoked': 'tinyint',
                    'created_at': 'datetime',
                    'updated_at': 'datetime',
                    'is_deleted': 'tinyint'
                }
                
                for field, expected_type in required_fields.items():
                    if field in columns:
                        print(f"   [OK] 字段 {field:25} 存在，类型: {columns[field]}")
                    else:
                        print(f"   [ERROR] 字段 {field:25} 不存在")
            else:
                print("   [ERROR] refresh_tokens 表不存在")
            
            print()
            
            # 3. 检查 email_verifications 表
            print("3. 检查 email_verifications 表...")
            result = conn.execute(text("SHOW TABLES LIKE 'email_verifications'"))
            if result.fetchone():
                print("   [OK] email_verifications 表存在")
                
                result = conn.execute(text("DESCRIBE email_verifications"))
                columns = {row[0]: row[1] for row in result.fetchall()}
                
                required_fields = {
                    'id': 'int',
                    'user_id': 'int',
                    'email': 'varchar',
                    'verification_code': 'varchar',
                    'expires_at': 'datetime',
                    'is_used': 'tinyint',
                    'created_at': 'datetime',
                    'updated_at': 'datetime',
                    'is_deleted': 'tinyint'
                }
                
                for field, expected_type in required_fields.items():
                    if field in columns:
                        print(f"   [OK] 字段 {field:25} 存在，类型: {columns[field]}")
                    else:
                        print(f"   [ERROR] 字段 {field:25} 不存在")
            else:
                print("   [ERROR] email_verifications 表不存在")
            
            print()
            
            # 4. 检查现有表的 user_id 字段
            print("4. 检查现有表的 user_id 字段...")
            
            tables_to_check = ['knowledge_bases', 'documents', 'qa_sessions', 'operation_logs']
            for table_name in tables_to_check:
                result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                if result.fetchone():
                    result = conn.execute(text(f"SHOW COLUMNS FROM {table_name} LIKE 'user_id'"))
                    column_info = result.fetchone()
                    if column_info:
                        print(f"   [OK] {table_name:20} 表有 user_id 字段，类型: {column_info[1]}")
                    else:
                        print(f"   [ERROR] {table_name:20} 表缺少 user_id 字段")
                else:
                    print(f"   [WARNING] {table_name:20} 表不存在（可能尚未创建）")
            
            print()
            
            # 5. 检查外键约束
            print("5. 检查外键约束...")
            result = conn.execute(text("""
                SELECT 
                    TABLE_NAME,
                    COLUMN_NAME,
                    CONSTRAINT_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                AND REFERENCED_TABLE_NAME = 'users'
                ORDER BY TABLE_NAME, CONSTRAINT_NAME
            """))
            foreign_keys = result.fetchall()
            
            if foreign_keys:
                print(f"   [OK] 找到 {len(foreign_keys)} 个指向 users 表的外键:")
                for fk in foreign_keys:
                    print(f"   - {fk[0]:20} . {fk[1]:15} -> {fk[3]}.{fk[4]} ({fk[2]})")
            else:
                print("   [ERROR] 未找到指向 users 表的外键")
            
            print()
            
            # 6. 检查数据统计
            print("6. 数据统计...")
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.fetchone()[0]
                print(f"   [INFO] users 表中的记录数: {user_count}")
                
                result = conn.execute(text("SELECT COUNT(*) FROM refresh_tokens"))
                token_count = result.fetchone()[0]
                print(f"   [INFO] refresh_tokens 表中的记录数: {token_count}")
                
                result = conn.execute(text("SELECT COUNT(*) FROM email_verifications"))
                verification_count = result.fetchone()[0]
                print(f"   [INFO] email_verifications 表中的记录数: {verification_count}")
            except Exception as e:
                print(f"   [WARNING] 无法获取数据统计: {e}")
        
        print()
        print("=" * 60)
        print("验证完成！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_migration()
