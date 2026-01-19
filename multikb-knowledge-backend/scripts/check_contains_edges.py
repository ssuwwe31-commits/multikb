"""
检查 contains 边是否存在
"""

import os
import sys
from pathlib import Path
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config


def load_env_file():
    """从 .env 文件加载环境变量"""
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ.setdefault(key, value)


def check_contains_edges(repo_id: int):
    """检查 contains 边"""
    load_env_file()
    
    nebula_hosts_str = os.getenv('NEBULA_HOSTS', '127.0.0.1:9669')
    nebula_user = os.getenv('NEBULA_USER', 'root')
    nebula_password = os.getenv('NEBULA_PASSWORD', 'password')
    space = "multikb_knowledge"
    repo_vid = f"code_repository_{repo_id}"
    
    if ':' in nebula_hosts_str:
        if ',' in nebula_hosts_str:
            nebula_hosts = []
            for host_str in nebula_hosts_str.split(','):
                host_parts = host_str.strip().split(':')
                if len(host_parts) == 2:
                    nebula_hosts.append((host_parts[0].strip(), int(host_parts[1].strip())))
        else:
            host_parts = nebula_hosts_str.split(':')
            nebula_host = host_parts[0]
            nebula_port = int(host_parts[1])
            nebula_hosts = [(nebula_host, nebula_port)]
    else:
        nebula_hosts = [('127.0.0.1', 9669)]
    
    config = Config()
    config.max_connection_pool_size = 10
    connection_pool = ConnectionPool()
    
    try:
        if not connection_pool.init(nebula_hosts, config):
            print("[FAIL] Failed to initialize connection pool")
            return
        
        session = connection_pool.get_session(nebula_user, nebula_password)
        result = session.execute(f"USE {space};")
        if not result.is_succeeded():
            print(f"[FAIL] Failed to switch to space: {result.error_msg()}")
            session.release()
            return
        
        # 检查所有 contains 边
        print(f"[Check 1] Checking all contains edges from {repo_vid}...")
        check_edges_nGQL = f'''
        MATCH (repo)-[e:contains]->(file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(e) as edge_count, id(file) as file_vid
        LIMIT 10;
        '''
        result = session.execute(check_edges_nGQL)
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                for i, col_name in enumerate(keys):
                    if col_name == 'edge_count':
                        count = row[i].as_int()
                        print(f"[OK] Found {count} contains edges")
                    elif col_name == 'file_vid':
                        vid = str(row[i])
                        print(f"   File VID: {vid}")
        else:
            print(f"[FAIL] No contains edges found")
            if not result.is_succeeded():
                print(f"   Error: {result.error_msg()}")
        
        # 检查所有 contains 边（不指定标签）
        print(f"\n[Check 2] Checking all contains edges (any type)...")
        check_all_edges_nGQL = f'''
        MATCH (repo)-[e:contains]->(file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(e) as edge_count;
        '''
        result = session.execute(check_all_edges_nGQL)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'edge_count':
                    count = row[i].as_int()
                    print(f"[OK] Total contains edges: {count}")
        
        # 检查是否有任何边从仓库节点发出
        print(f"\n[Check 3] Checking all edges from {repo_vid}...")
        check_any_edges_nGQL = f'''
        MATCH (repo)-[e]->(target)
        WHERE id(repo) == "{repo_vid}"
        RETURN type(e) as edge_type, count(*) as count;
        '''
        result = session.execute(check_any_edges_nGQL)
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            print(f"[OK] Found edges:")
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                edge_type = None
                count = None
                for i, col_name in enumerate(keys):
                    if col_name == 'edge_type':
                        edge_type = str(row[i])
                    elif col_name == 'count':
                        count = row[i].as_int()
                if edge_type and count:
                    print(f"   {edge_type}: {count}")
        else:
            print(f"[FAIL] No edges found from repository")
            if not result.is_succeeded():
                print(f"   Error: {result.error_msg()}")
        
        session.release()
        
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection_pool.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            repo_id = int(sys.argv[1])
            check_contains_edges(repo_id)
        except ValueError:
            print(f"Error: Invalid repo_id")
            sys.exit(1)
    else:
        print("Usage: python check_contains_edges.py [repo_id]")
        sys.exit(1)
