"""
执行单个迁移脚本
用于执行知识库共享功能的迁移
"""

import os
import sys
from pathlib import Path
import pymysql
from dotenv import load_dotenv

# 加载.env文件
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    # 避免 Windows 控制台编码问题，不打印特殊符号
    print(f"[INFO] 已加载环境变量文件: {env_file}")
else:
    print(f"[WARN] 未找到 .env 文件: {env_file}，使用系统环境变量")

# 从环境变量读取数据库配置
def get_db_config():
    """从环境变量读取数据库配置"""
    # 优先使用DATABASE_URL
    database_url = os.getenv("DATABASE_URL", "")
    
    if database_url and database_url.startswith("mysql+pymysql://"):
        # 解析DATABASE_URL: mysql+pymysql://user:password@host:port/database
        url = database_url.replace("mysql+pymysql://", "")
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
        "user": os.getenv("MYSQL_USER", "user"),
        "password": os.getenv("MYSQL_PASSWORD", "password"),
        "database": os.getenv("MYSQL_DATABASE", "spx_knowledge")
    }

def execute_sql_file(connection, sql_file: Path):
    """执行SQL文件"""
    print(f"\n[INFO] 执行迁移脚本: {sql_file.name}")
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        cursor = connection.cursor()
        
        # 执行整个SQL文件
        try:
            # 分割SQL语句（以分号分隔）
            statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                stripped = line.strip()
                # 跳过空行和注释
                if not stripped or stripped.startswith('--'):
                    continue
                
                current_statement += line + '\n'
                
                # 如果行以分号结尾，说明是一个完整的语句
                if stripped.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
            
            # 执行所有SQL语句
            success_count = 0
            error_count = 0
            
            for statement in statements:
                if not statement:
                    continue
                try:
                    cursor.execute(statement)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ SQL语句执行失败: {str(e)[:200]}")
                    print(f"     语句: {statement[:300]}...")
            
            connection.commit()
            cursor.close()
            
            if error_count == 0:
                print(f"  [INFO] 成功执行 {success_count} 条 SQL 语句")
                return True
            else:
                print(f"  [WARN] 成功 {success_count} 条，失败 {error_count} 条")
                return False

        except Exception as e:
            print(f"  [ERROR] 执行失败: {e}")
            connection.rollback()
            return False

    except Exception as e:
        print(f"  [ERROR] 读取文件失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("知识库共享功能迁移脚本")
    print("=" * 60)
    
    # 获取数据库配置
    db_config = get_db_config()
    print(f"\n[INFO] 数据库配置:")
    print(f"   主机: {db_config['host']}:{db_config['port']}")
    print(f"   用户: {db_config['user']}")
    print(f"   数据库: {db_config['database']}")
    
    # 连接数据库
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"\n[INFO] 数据库连接成功")
    except Exception as e:
        print(f"\n[ERROR] 数据库连接失败: {e}")
        print("\n提示: 请确保:")
        print("  1. MySQL 服务已启动")
        print("  2. .env 文件中的数据库配置正确")
        print("  3. 已安装 pymysql: pip install pymysql")
        sys.exit(1)
    
    # 获取迁移脚本
    migration_file = Path(__file__).parent.parent / "migrations" / "2025020201_kb_members_and_visibility.sql"
    if not migration_file.exists():
        print(f"\n❌ 迁移脚本不存在: {migration_file}")
        connection.close()
        sys.exit(1)
    
    # 执行迁移
    print(f"\n[INFO] 开始执行迁移...")
    if execute_sql_file(connection, migration_file):
        print(f"\n[INFO] 迁移完成！")
    else:
        print(f"\n[ERROR] 迁移失败，请检查错误信息")
        connection.close()
        sys.exit(1)
    
    # 关闭连接
    connection.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
