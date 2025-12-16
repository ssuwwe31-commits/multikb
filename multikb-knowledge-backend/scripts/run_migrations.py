#!/usr/bin/env python
"""
执行实体类型相关的数据库迁移脚本
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
load_dotenv()

def execute_sql_file(cursor, sql_file_path):
    """执行SQL文件"""
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 移除USE语句（已经在连接时指定了数据库）
    sql_content = sql_content.replace('USE `spx_knowledge`;', '').replace('USE spx_knowledge;', '')
    
    # 使用pymysql的multi=True执行多条SQL语句
    try:
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
                    if 'already exists' in str(e).lower() or 'Duplicate' in str(e):
                        print(f"  跳过（已存在）: {statement[:50]}...")
                        continue
                    raise
        
        return executed
    except Exception as e:
        print(f"执行SQL文件时出错: {e}")
        raise

def main():
    """主函数"""
    # 获取数据库配置
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', 3306))
    user = os.getenv('MYSQL_USER', 'user')
    password = os.getenv('MYSQL_PASSWORD', 'password')
    database = os.getenv('MYSQL_DATABASE', 'spx_knowledge')
    
    print(f"连接数据库: {user}@{host}:{port}/{database}")
    
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
        
        # 执行迁移脚本1
        print("\n执行迁移脚本1: 2025120802_entity_types_tables.sql")
        migration1 = project_root / 'migrations' / '2025120802_entity_types_tables.sql'
        if migration1.exists():
            executed = execute_sql_file(cursor, migration1)
            conn.commit()
            print(f"✓ 迁移脚本1执行成功，执行了 {executed} 条SQL语句")
        else:
            print(f"✗ 迁移脚本1不存在: {migration1}")
        
        # 执行迁移脚本2
        print("\n执行迁移脚本2: 2025120803_industry_template_entity_types.sql")
        migration2 = project_root / 'migrations' / '2025120803_industry_template_entity_types.sql'
        if migration2.exists():
            executed = execute_sql_file(cursor, migration2)
            conn.commit()
            print(f"✓ 迁移脚本2执行成功，执行了 {executed} 条SQL语句")
        else:
            print(f"✗ 迁移脚本2不存在: {migration2}")
        
        # 验证数据
        print("\n验证数据...")
        cursor.execute('SELECT COUNT(*) FROM entity_types')
        count = cursor.fetchone()[0]
        print(f"✓ 实体类型总数: {count}")
        
        cursor.execute('SELECT code, name, is_system FROM entity_types ORDER BY sort_order')
        types = cursor.fetchall()
        print(f"\n实体类型列表（共{len(types)}个）:")
        for t in types:
            system_tag = "系统" if t[2] else "自定义"
            print(f"  - {t[0]:20s} {t[1]:15s} ({system_tag})")
        
        cursor.close()
        conn.close()
        
        print("\n✓ 迁移完成！")
        
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
