#!/usr/bin/env python
"""
检查数据库状态并执行必要的迁移
检查 entity_types 表的 metadata 列，如果存在则重命名为 meta_data
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import pymysql

# 加载环境变量
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"警告: .env 文件不存在: {env_file}")
    print("将使用默认配置或环境变量")

def check_table_and_column(cursor, db_name, table_name, column_name):
    """检查表和列是否存在"""
    # 检查表是否存在
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = %s
    """, (db_name, table_name))
    table_exists = cursor.fetchone()[0] > 0
    
    if not table_exists:
        return False, False
    
    # 检查列是否存在
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = %s 
        AND COLUMN_NAME = %s
    """, (db_name, table_name, column_name))
    column_exists = cursor.fetchone()[0] > 0
    
    return True, column_exists

def execute_sql_file(cursor, sql_file_path):
    """执行SQL文件"""
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 移除USE语句（已经在连接时指定了数据库）
    sql_content = sql_content.replace('USE `spx_knowledge`;', '').replace('USE spx_knowledge;', '')
    
    # 分割SQL语句
    statements = []
    current_statement = []
    for line in sql_content.split('\n'):
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith('--'):
            continue
        current_statement.append(line)
        # 如果行以分号结尾，说明是一个完整的SQL语句
        if line.endswith(';'):
            statement = ' '.join(current_statement)
            if statement and statement != ';':
                statements.append(statement)
            current_statement = []
    
    # 执行所有语句
    executed = 0
    for statement in statements:
        if statement.strip() and statement.strip() != ';':
            try:
                cursor.execute(statement)
                executed += 1
            except Exception as e:
                # 如果是表已存在的错误，忽略
                error_msg = str(e).lower()
                if 'already exists' in error_msg or 'duplicate' in error_msg:
                    print(f"  跳过（已存在）: {statement[:50]}...")
                    continue
                raise
    
    return executed

def main():
    """主函数"""
    # 获取数据库配置
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', 3306))
    user = os.getenv('MYSQL_USER', 'user')
    password = os.getenv('MYSQL_PASSWORD', 'password')
    database = os.getenv('MYSQL_DATABASE', 'spx_knowledge')
    
    print("=" * 60)
    print("数据库状态检查与迁移工具")
    print("=" * 60)
    print(f"数据库: {user}@{host}:{port}/{database}")
    print()
    
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # 检查 entity_types 表和 metadata 列
        print("检查 entity_types 表状态...")
        table_exists, metadata_column_exists = check_table_and_column(
            cursor, database, 'entity_types', 'metadata'
        )
        
        if not table_exists:
            print("✓ entity_types 表不存在，将执行创建表的迁移")
            print("\n执行迁移脚本1: 2025120802_entity_types_tables.sql")
            migration1 = project_root / 'migrations' / '2025120802_entity_types_tables.sql'
            if migration1.exists():
                executed = execute_sql_file(cursor, migration1)
                conn.commit()
                print(f"✓ 迁移脚本1执行成功，执行了 {executed} 条SQL语句")
            else:
                print(f"✗ 迁移脚本1不存在: {migration1}")
                return False
            
            print("\n执行迁移脚本2: 2025120803_industry_template_entity_types.sql")
            migration2 = project_root / 'migrations' / '2025120803_industry_template_entity_types.sql'
            if migration2.exists():
                executed = execute_sql_file(cursor, migration2)
                conn.commit()
                print(f"✓ 迁移脚本2执行成功，执行了 {executed} 条SQL语句")
            else:
                print(f"✗ 迁移脚本2不存在: {migration2}")
                return False
                
        elif metadata_column_exists:
            print("⚠ 发现 metadata 列，需要重命名为 meta_data")
            print("\n执行列重命名迁移: 2025120804_rename_metadata_to_meta_data.sql")
            migration_rename = project_root / 'migrations' / '2025120804_rename_metadata_to_meta_data.sql'
            if migration_rename.exists():
                try:
                    executed = execute_sql_file(cursor, migration_rename)
                    conn.commit()
                    print(f"✓ 列重命名成功，执行了 {executed} 条SQL语句")
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'unknown column' in error_msg or 'doesn\'t exist' in error_msg:
                        print(f"⚠ 列已不存在或已重命名: {e}")
                        print("  继续执行其他迁移...")
                    else:
                        raise
            else:
                print(f"✗ 迁移脚本不存在: {migration_rename}")
                return False
        else:
            print("✓ entity_types 表存在，且列名正确（meta_data）")
            # 检查是否有 meta_data 列
            _, meta_data_exists = check_table_and_column(
                cursor, database, 'entity_types', 'meta_data'
            )
            if not meta_data_exists:
                print("⚠ 表存在但缺少 meta_data 列，执行创建表的迁移（会跳过已存在的表）")
                migration1 = project_root / 'migrations' / '2025120802_entity_types_tables.sql'
                if migration1.exists():
                    executed = execute_sql_file(cursor, migration1)
                    conn.commit()
                    print(f"✓ 迁移脚本执行成功，执行了 {executed} 条SQL语句")
        
        # 验证数据
        print("\n验证数据...")
        try:
            cursor.execute('SELECT COUNT(*) FROM entity_types')
            count = cursor.fetchone()[0]
            print(f"✓ 实体类型总数: {count}")
            
            if count > 0:
                cursor.execute('SELECT code, name, is_system FROM entity_types ORDER BY sort_order LIMIT 10')
                types = cursor.fetchall()
                print(f"\n实体类型列表（前10个）:")
                for t in types:
                    system_tag = "系统" if t[2] else "自定义"
                    print(f"  - {t[0]:20s} {t[1]:15s} ({system_tag})")
        except Exception as e:
            print(f"⚠ 验证数据时出错（可能是表不存在）: {e}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ 迁移完成！")
        print("=" * 60)
        return True
        
    except pymysql.Error as e:
        print(f"\n✗ 数据库连接失败: {e}")
        print("\n请检查:")
        print("  1. 数据库服务是否运行")
        print("  2. .env 文件中的数据库配置是否正确")
        print("  3. 数据库用户是否有足够的权限")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

