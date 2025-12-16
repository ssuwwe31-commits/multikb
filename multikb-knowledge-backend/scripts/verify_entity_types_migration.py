#!/usr/bin/env python
"""
验证实体类型迁移结果
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import pymysql

load_dotenv()

def verify():
    """验证实体类型迁移"""
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'user'),
        'password': os.getenv('MYSQL_PASSWORD', 'password'),
        'database': os.getenv('MYSQL_DATABASE', 'spx_knowledge'),
        'charset': 'utf8mb4'
    }
    
    print("=" * 70)
    print("验证实体类型迁移结果")
    print("=" * 70)
    
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute('SHOW TABLES LIKE "entity_types"')
        table_exists = cursor.fetchone() is not None
        print(f"\n1. entity_types表: {'✓ 存在' if table_exists else '✗ 不存在'}")
        
        cursor.execute('SHOW TABLES LIKE "knowledge_base_entity_types"')
        kb_table_exists = cursor.fetchone() is not None
        print(f"2. knowledge_base_entity_types表: {'✓ 存在' if kb_table_exists else '✗ 不存在'}")
        
        if table_exists:
            # 检查数据
            cursor.execute('SELECT COUNT(*) FROM entity_types')
            total = cursor.fetchone()[0]
            print(f"\n3. 实体类型总数: {total}")
            
            cursor.execute('SELECT COUNT(*) FROM entity_types WHERE is_system = TRUE')
            system_count = cursor.fetchone()[0]
            print(f"4. 系统类型数量: {system_count}")
            
            cursor.execute('SELECT COUNT(*) FROM entity_types WHERE is_system = FALSE')
            custom_count = cursor.fetchone()[0]
            print(f"5. 自定义类型数量: {custom_count}")
            
            # 列出系统类型
            cursor.execute('SELECT code, name FROM entity_types WHERE is_system = TRUE ORDER BY sort_order')
            system_types = cursor.fetchall()
            print(f"\n6. 系统类型列表（{len(system_types)}个）:")
            for t in system_types:
                print(f"   - {t[0]:15s} {t[1]}")
            
            # 列出行业模板类型
            cursor.execute('SELECT code, name FROM entity_types WHERE is_system = FALSE ORDER BY sort_order')
            custom_types = cursor.fetchall()
            print(f"\n7. 行业模板类型列表（{len(custom_types)}个）:")
            for t in custom_types:
                print(f"   - {t[0]:20s} {t[1]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        if table_exists and total >= 21:
            print("✓ 迁移验证通过！")
        else:
            print("⚠ 迁移可能未完成，请检查")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    verify()
