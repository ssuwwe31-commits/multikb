"""
检查数据库中是否有 user_id 字段
"""

import sys
import io
from pathlib import Path

# 设置标准输出为 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from app.config.settings import settings
import pymysql

def check_user_id_fields():
    """检查 documents 和 knowledge_bases 表是否有 user_id 字段"""
    try:
        # 从 DATABASE_URL 解析连接信息
        db_url = settings.DATABASE_URL
        # 格式: mysql+pymysql://user:password@host:port/database
        if db_url.startswith('mysql+pymysql://'):
            db_url = db_url.replace('mysql+pymysql://', '')
        
        parts = db_url.split('@')
        if len(parts) != 2:
            print(f"❌ 无法解析数据库URL: {db_url}")
            return
        
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        
        if len(user_pass) != 2 or len(host_db) != 2:
            print(f"❌ 无法解析数据库URL: {db_url}")
            return
        
        username = user_pass[0]
        password = user_pass[1]
        host_port = host_db[0].split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 3306
        database = host_db[1]
        
        print(f"📊 连接数据库: {host}:{port}/{database}")
        print(f"   用户名: {username}")
        
        # 连接数据库
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        
        try:
            with connection.cursor() as cursor:
                # 检查 documents 表
                print("\n" + "="*60)
                print("检查 documents 表")
                print("="*60)
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'documents'
                    AND COLUMN_NAME = 'user_id'
                """, (database,))
                
                result = cursor.fetchone()
                if result:
                    print(f"✅ documents.user_id 字段存在")
                    print(f"   类型: {result[1]}")
                    print(f"   可空: {result[2]}")
                    print(f"   注释: {result[3]}")
                else:
                    print(f"❌ documents.user_id 字段不存在")
                
                # 检查外键约束
                cursor.execute("""
                    SELECT CONSTRAINT_NAME
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'documents'
                    AND CONSTRAINT_TYPE = 'FOREIGN KEY'
                    AND CONSTRAINT_NAME LIKE '%%user%%'
                """, (database,))
                
                fk_result = cursor.fetchone()
                if fk_result:
                    print(f"✅ documents.user_id 外键约束存在: {fk_result[0]}")
                else:
                    print(f"⚠️  documents.user_id 外键约束不存在")
                
                # 检查 knowledge_bases 表
                print("\n" + "="*60)
                print("检查 knowledge_bases 表")
                print("="*60)
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'knowledge_bases'
                    AND COLUMN_NAME = 'user_id'
                """, (database,))
                
                result = cursor.fetchone()
                if result:
                    print(f"✅ knowledge_bases.user_id 字段存在")
                    print(f"   类型: {result[1]}")
                    print(f"   可空: {result[2]}")
                    print(f"   注释: {result[3]}")
                else:
                    print(f"❌ knowledge_bases.user_id 字段不存在")
                
                # 检查外键约束
                cursor.execute("""
                    SELECT CONSTRAINT_NAME
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'knowledge_bases'
                    AND CONSTRAINT_TYPE = 'FOREIGN KEY'
                    AND CONSTRAINT_NAME LIKE '%%user%%'
                """, (database,))
                
                fk_result = cursor.fetchone()
                if fk_result:
                    print(f"✅ knowledge_bases.user_id 外键约束存在: {fk_result[0]}")
                else:
                    print(f"⚠️  knowledge_bases.user_id 外键约束不存在")
                
                # 检查现有数据
                print("\n" + "="*60)
                print("检查现有数据")
                print("="*60)
                cursor.execute("SELECT COUNT(*) FROM documents WHERE user_id IS NULL")
                null_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM documents")
                total_count = cursor.fetchone()[0]
                print(f"documents 表: 总数 {total_count}, user_id 为 NULL 的记录 {null_count}")
                
                cursor.execute("SELECT COUNT(*) FROM knowledge_bases WHERE user_id IS NULL")
                null_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM knowledge_bases")
                total_count = cursor.fetchone()[0]
                print(f"knowledge_bases 表: 总数 {total_count}, user_id 为 NULL 的记录 {null_count}")
                
        finally:
            connection.close()
            print("\n✅ 数据库连接已关闭")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_user_id_fields()
