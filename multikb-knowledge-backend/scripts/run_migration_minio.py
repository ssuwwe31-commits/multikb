#!/usr/bin/env python3
"""
运行数据库迁移脚本：添加 MinIO 支持字段
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pymysql
from dotenv import load_dotenv

# 加载环境变量
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️ 未找到 .env 文件，使用默认配置")

# 从环境变量或直接读取配置
MYSQL_HOST = os.getenv('MYSQL_HOST', '192.168.131.42')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'user')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'spx_knowledge')

# 读取迁移脚本
migration_file = project_root / 'migrations' / '2026011901_add_minio_path_to_cache.sql'
if not migration_file.exists():
    print(f"[ERROR] 迁移脚本不存在: {migration_file}")
    sys.exit(1)

print(f"[INFO] 读取迁移脚本: {migration_file}")
with open(migration_file, 'r', encoding='utf-8') as f:
    migration_sql = f.read()

# 连接数据库
print(f"[INFO] 连接数据库: {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
try:
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    print("[SUCCESS] 数据库连接成功")
except Exception as e:
    print(f"[ERROR] 数据库连接失败: {e}")
    sys.exit(1)

# 执行迁移
try:
    cursor = conn.cursor()
    
    # 分割 SQL 语句（按分号分割，过滤注释和空行）
    lines = migration_sql.split('\n')
    statements = []
    current_statement = []
    
    for line in lines:
        stripped = line.strip()
        # 跳过空行和注释行
        if not stripped or stripped.startswith('--'):
            continue
        # 添加到当前语句
        current_statement.append(stripped)
        # 如果行以分号结尾，完成一个语句
        if stripped.endswith(';'):
            statement = ' '.join(current_statement).rstrip(';').strip()
            if statement:
                statements.append(statement)
            current_statement = []
    
    # 处理最后一个语句（如果没有分号结尾）
    if current_statement:
        statement = ' '.join(current_statement).strip()
        if statement:
            statements.append(statement)
    
    print(f"\n[INFO] 开始执行迁移，共 {len(statements)} 条 SQL 语句\n")
    
    for i, statement in enumerate(statements, 1):
        if not statement:
            continue
        
        # 显示语句的前80个字符
        preview = statement[:80] + '...' if len(statement) > 80 else statement
        print(f"[{i}/{len(statements)}] 执行: {preview}")
        try:
            cursor.execute(statement)
            conn.commit()
            print(f"  [SUCCESS] 执行成功\n")
        except Exception as e:
            error_code = e.args[0] if e.args else None
            error_msg = str(e)
            
            # 检查是否是字段已存在的错误
            if error_code == 1060 and 'Duplicate column name' in error_msg:
                print(f"  [WARNING] 字段已存在，跳过: {error_msg}\n")
            elif error_code == 1061 and 'Duplicate key name' in error_msg:
                print(f"  [WARNING] 索引已存在，跳过: {error_msg}\n")
            else:
                print(f"  [ERROR] 执行失败: {e}\n")
                raise
    
    print("=" * 60)
    print("[SUCCESS] 迁移完成！")
    print("=" * 60)
    print("\n迁移内容:")
    print("  - 添加 minio_path 字段 (VARCHAR(500))")
    print("  - 添加 file_size 字段 (BIGINT)")
    print("  - 添加 is_compressed 字段 (BOOLEAN)")
    print("  - 修改 cache_data 字段为可选 (JSON NULL)")
    print("  - 添加 idx_minio_path 索引")
    print("\n现在系统可以正常使用 MinIO 存储大文件了！")
    
except Exception as e:
    print(f"\n[ERROR] 迁移失败: {e}")
    conn.rollback()
    sys.exit(1)
finally:
    cursor.close()
    conn.close()
    print("\n[INFO] 数据库连接已关闭")
