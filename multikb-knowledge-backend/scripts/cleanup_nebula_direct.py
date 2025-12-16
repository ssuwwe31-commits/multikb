#!/usr/bin/env python3
"""
直接清理NebulaGraph数据（不依赖项目模块）
使用nebula3客户端直接连接
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"[INFO] 已加载环境变量文件: {env_file}")
else:
    print(f"[WARN] 未找到 .env 文件: {env_file}，使用系统环境变量")

# 从环境变量读取NebulaGraph配置
def get_nebula_config():
    """从环境变量读取NebulaGraph配置"""
    hosts_str = os.getenv("NEBULA_HOSTS", "127.0.0.1:9669")
    # 解析hosts（支持多个，格式：host1:port1,host2:port2 或 host:port）
    hosts = []
    for host_port in hosts_str.split(','):
        host_port = host_port.strip()
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            hosts.append((host, int(port)))
        else:
            hosts.append((host_port, 9669))
    
    return {
        "hosts": hosts,
        "user": os.getenv("NEBULA_USER", "root"),
        "password": os.getenv("NEBULA_PASSWORD", "nebula"),
    }

kb_id = 4
space = f"kb_{kb_id}"

print("=" * 60)
print(f"开始清理知识库 {kb_id} 的NebulaGraph数据...")
print(f"Space: {space}")
print("=" * 60)

# 获取配置
config = get_nebula_config()
print(f"\n[NebulaGraph连接] {config['user']}@{config['hosts']}")

try:
    from nebula3.gclient.net import ConnectionPool
    from nebula3.Config import Config
    from nebula3.data.ResultSet import ResultSet
    
    # 创建连接池
    nebula_config = Config()
    nebula_config.max_connection_pool_size = 10
    
    pool = ConnectionPool()
    if not pool.init(config['hosts'], nebula_config):
        print("[ERROR] 连接池初始化失败")
        sys.exit(1)
    
    print("[OK] 连接池初始化成功")
    
    # 获取session
    session = pool.get_session(config['user'], config['password'])
    if not session:
        print("[ERROR] 无法获取session")
        sys.exit(1)
    
    print("[OK] 会话创建成功")
    
    try:
        # 切换到指定空间
        use_result = session.execute(f"USE {space};")
        if not use_result.is_succeeded():
            error_msg = use_result.error_msg()
            if "Space not found" in error_msg or "not exist" in error_msg.lower() or "SpaceNotFound" in error_msg:
                print(f"[INFO] NebulaGraph空间 {space} 不存在，无需清理")
                print("[SUCCESS] 清理完成（空间不存在）")
                session.release()
                pool.close()
                sys.exit(0)
            else:
                print(f"[ERROR] USE空间失败: {error_msg}")
                session.release()
                pool.close()
                sys.exit(1)
        
        print(f"[OK] 已切换到空间: {space}")
        
        # 查询所有实体
        print("\n[步骤1] 查询所有实体...")
        query_nGQL = """
        MATCH (n:entity)
        RETURN id(n) as vid, n.name as name, n.mysql_id as mysql_id
        LIMIT 10000;
        """
        
        result = session.execute(query_nGQL)
        if not result.is_succeeded():
            print(f"[ERROR] 查询失败: {result.error_msg()}")
            sys.exit(1)
        
        # 解析结果
        entities = []
        for row in result:
            vid = row.values[0].get_sVal().decode('utf-8') if row.values[0].get_sVal() else str(row.values[0])
            name = row.values[1].get_sVal().decode('utf-8') if len(row.values) > 1 and row.values[1].get_sVal() else 'N/A'
            entities.append({
                'vid': vid.strip('"\''),
                'name': name
            })
        
        print(f"[OK] 找到 {len(entities)} 个实体")
        
        if not entities:
            print("[INFO] NebulaGraph中没有实体数据，无需清理")
            sys.exit(0)
        
        # 删除所有实体
        print("\n[步骤2] 删除所有实体（会同时删除相关关系）...")
        deleted_count = 0
        failed_count = 0
        
        for idx, entity in enumerate(entities):
            vid = entity['vid']
            name = entity['name']
            
            try:
                # DELETE VERTEX会自动删除相关的边
                delete_nGQL = f'DELETE VERTEX "{vid}";'
                delete_result = session.execute(delete_nGQL)
                
                if delete_result.is_succeeded():
                    deleted_count += 1
                    if deleted_count % 50 == 0:
                        print(f"   已删除 {deleted_count}/{len(entities)} 个实体...")
                else:
                    failed_count += 1
                    print(f"[WARN] 删除实体失败: vid={vid}, name={name}, 错误={delete_result.error_msg()}")
            except Exception as e:
                failed_count += 1
                print(f"[WARN] 删除实体失败: vid={vid}, name={name}, 错误={e}")
        
        print(f"\n[OK] 删除完成:")
        print(f"   成功: {deleted_count}")
        print(f"   失败: {failed_count}")
        
        # 验证清理结果
        print("\n[步骤3] 验证清理结果...")
        result = session.execute(query_nGQL)
        if result.is_succeeded():
            remaining_count = sum(1 for _ in result)
            if remaining_count == 0:
                print(f"[SUCCESS] NebulaGraph数据已完全清理！")
            else:
                print(f"[WARN] 仍有 {remaining_count} 个实体未清理完成")
        else:
            print(f"[INFO] 验证查询完成")
        
    finally:
        session.release()
        pool.close()
        
except ImportError:
    print("\n[ERROR] 错误：缺少 nebula3 模块")
    print("请安装: pip install nebula3-python")
    print("或者激活项目的conda环境后执行")
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] 执行失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("[SUCCESS] NebulaGraph清理完成！")
print("=" * 60)

