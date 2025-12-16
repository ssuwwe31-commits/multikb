#!/usr/bin/env python3
"""
直接清理知识库4的知识图谱数据
使用pymysql直接连接数据库，不依赖SQLAlchemy
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import pymysql

# 加载.env文件
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"[INFO] 已加载环境变量文件: {env_file}")
else:
    print(f"[WARN] 未找到 .env 文件: {env_file}，使用系统环境变量")

# 从环境变量读取数据库配置
def get_db_config():
    """从环境变量读取数据库配置"""
    database_url = os.getenv("DATABASE_URL", "")
    
    if database_url and "mysql" in database_url:
        # 解析DATABASE_URL: mysql+pymysql://user:password@host:port/database
        url = database_url.replace("mysql+pymysql://", "").replace("mysql://", "")
        parts = url.split("@")
        if len(parts) == 2:
            user_pass = parts[0].split(":")
            host_db = parts[1].split("/")
            if len(host_db) == 2:
                host_port = host_db[0].split(":")
                return {
                    "host": host_port[0],
                    "port": int(host_port[1]) if len(host_port) > 1 else 3306,
                    "user": user_pass[0],
                    "password": user_pass[1] if len(user_pass) > 1 else "",
                    "database": host_db[1]
                }
    
    # 使用分项配置
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "spx_knowledge")
    }

kb_id = 4

print("=" * 60)
print(f"开始清理知识库 {kb_id} 的知识图谱数据...")
print("=" * 60)

# 获取数据库配置
db_config = get_db_config()
print(f"\n[数据库连接] {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")

try:
    # 连接MySQL
    connection = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            # 步骤1：删除实体-文档关联
            print("\n[步骤1] 删除实体-文档关联...")
            # 先查询需要删除的entity_id
            cursor.execute("""
                SELECT id FROM knowledge_graph_entities
                WHERE knowledge_base_id = %s AND is_deleted = FALSE
            """, (kb_id,))
            entity_ids = [row['id'] for row in cursor.fetchall()]
            
            if entity_ids:
                placeholders = ','.join(['%s'] * len(entity_ids))
                sql1 = f"""
                    DELETE FROM knowledge_graph_entity_documents
                    WHERE entity_id IN ({placeholders})
                """
                count1 = cursor.execute(sql1, entity_ids)
            else:
                count1 = 0
            print(f"[OK] 已删除 {count1} 条实体-文档关联记录")
            
            # 步骤2：删除关系
            print("\n[步骤2] 删除关系...")
            sql2 = """
                DELETE FROM knowledge_graph_relationships
                WHERE knowledge_base_id = %s AND is_deleted = FALSE
            """
            count2 = cursor.execute(sql2, (kb_id,))
            print(f"[OK] 已删除 {count2} 条关系记录")
            
            # 步骤3：删除实体
            print("\n[步骤3] 删除实体...")
            sql3 = """
                DELETE FROM knowledge_graph_entities
                WHERE knowledge_base_id = %s AND is_deleted = FALSE
            """
            count3 = cursor.execute(sql3, (kb_id,))
            print(f"[OK] 已删除 {count3} 条实体记录")
            
            # 步骤4：删除提取任务
            print("\n[步骤4] 删除提取任务...")
            sql4 = """
                DELETE FROM knowledge_graph_extraction_tasks
                WHERE knowledge_base_id = %s AND is_deleted = FALSE
            """
            count4 = cursor.execute(sql4, (kb_id,))
            print(f"[OK] 已删除 {count4} 条提取任务记录")
            
            # 提交事务
            connection.commit()
            
            total = count1 + count2 + count3 + count4
            print("\n" + "=" * 60)
            print(f"[SUCCESS] MySQL数据清理完成！")
            print(f"   总计删除：{total} 条记录")
            print("=" * 60)
            
            # 验证清理结果
            print("\n[验证] 检查清理结果...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM knowledge_graph_entities
                WHERE knowledge_base_id = %s AND is_deleted = FALSE
            """, (kb_id,))
            remaining_entities = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM knowledge_graph_relationships
                WHERE knowledge_base_id = %s AND is_deleted = FALSE
            """, (kb_id,))
            remaining_relationships = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM knowledge_graph_extraction_tasks
                WHERE knowledge_base_id = %s AND is_deleted = FALSE
            """, (kb_id,))
            remaining_tasks = cursor.fetchone()['count']
            
            print(f"   剩余实体：{remaining_entities}")
            print(f"   剩余关系：{remaining_relationships}")
            print(f"   剩余任务：{remaining_tasks}")
            
            if remaining_entities == 0 and remaining_relationships == 0:
                print("[SUCCESS] 知识库数据已完全清理！")
            else:
                print("[WARN] 仍有数据未清理完成")
            
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        connection.close()
        
except ImportError:
    print("\n[ERROR] 错误：缺少 pymysql 模块")
    print("请安装: pip install pymysql python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] MySQL清理失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 清理NebulaGraph数据
print("\n[步骤5] 清理NebulaGraph数据...")
print("[WARN] 注意：NebulaGraph清理需要Python环境支持")
print("   可以使用API清理：POST /api/knowledge-graph/cleanup/orphaned-data?knowledge_base_id=4")
print("   或者在NebulaGraph控制台执行：DROP SPACE IF EXISTS kb_4;")
print("\n[INFO] 提示：由于MySQL数据已清理，下次查询可视化数据时会自动清理NebulaGraph中的孤立数据")

