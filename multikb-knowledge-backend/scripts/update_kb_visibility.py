"""
更新知识库 visibility 字段的迁移脚本
根据成员数量自动更新知识库的 visibility 字段
"""

import os
import sys
from pathlib import Path
import pymysql
from dotenv import load_dotenv

# 确保输出编码为 UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# 加载.env文件（从项目根目录）
# 尝试多个可能的路径
possible_env_paths = [
    Path(__file__).parent.parent.parent / ".env",  # 项目根目录
    Path(__file__).parent.parent / ".env",  # multikb-knowledge-backend目录
]

env_file = None
for path in possible_env_paths:
    if path.exists():
        env_file = path
        break

if env_file:
    load_dotenv(env_file)
    print(f"[INFO] 已加载环境变量文件: {env_file}")
else:
    # 如果找不到，尝试从当前工作目录查找
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        load_dotenv(cwd_env)
        print(f"[INFO] 已加载环境变量文件: {cwd_env}")
    else:
        print(f"[WARN] 未找到.env文件，使用系统环境变量")

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

def execute_sql(connection, sql: str):
    """执行SQL语句"""
    try:
        cursor = connection.cursor()
        cursor.execute(sql)
        affected_rows = cursor.rowcount
        connection.commit()
        cursor.close()
        return affected_rows
    except Exception as e:
        connection.rollback()
        raise e

def main():
    """主函数"""
    print("=" * 60)
    print("更新知识库 visibility 字段")
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
    
    try:
        # 执行更新SQL
        sql = """
        UPDATE `knowledge_bases` kb
        SET `visibility` = CASE
            WHEN (
                SELECT COUNT(*) 
                FROM `knowledge_base_members` m 
                WHERE m.`knowledge_base_id` = kb.`id`
            ) > 1 THEN 'shared'
            ELSE 'private'
        END
        WHERE `is_deleted` = 0;
        """
        
        print(f"\n[INFO] 开始执行更新...")
        affected_rows = execute_sql(connection, sql)
        print(f"\n[INFO] 更新完成！共更新 {affected_rows} 条记录")
        
        # 查询更新结果统计
        cursor = connection.cursor()
        cursor.execute("SELECT `visibility`, COUNT(*) as count FROM `knowledge_bases` WHERE `is_deleted` = 0 GROUP BY `visibility`")
        results = cursor.fetchall()
        cursor.close()
        
        print(f"\n[INFO] 更新结果统计:")
        for row in results:
            print(f"   {row['visibility']}: {row['count']} 个知识库")
        
    except Exception as e:
        print(f"\n[ERROR] 更新失败: {e}")
        connection.rollback()
        connection.close()
        sys.exit(1)
    
    # 关闭连接
    connection.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
