"""
验证 contains 边是否存在
"""

import os
import sys
from pathlib import Path
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config


def load_env_file():
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


def verify_contains_edges(repo_id: int):
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
        
        # 方法1：使用 MATCH 查询
        print(f"[Method 1] Using MATCH query...")
        query1 = f'''
        MATCH (repo:code_repository)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(file) as file_count;
        '''
        result = session.execute(query1)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'file_count':
                    count = row[i].as_int()
                    print(f"[OK] Method 1: Found {count} files")
        else:
            print(f"[FAIL] Method 1 failed: {result.error_msg() if not result.is_succeeded() else 'No results'}")
        
        # 方法2：使用 GO 查询（NebulaGraph 原生语法）
        print(f"\n[Method 2] Using GO query...")
        query2 = f'''
        GO FROM "{repo_vid}" OVER contains
        YIELD dst(edge) as file_vid
        | YIELD count(*) as file_count;
        '''
        result = session.execute(query2)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'file_count':
                    count = row[i].as_int()
                    print(f"[OK] Method 2: Found {count} files")
        else:
            print(f"[FAIL] Method 2 failed: {result.error_msg() if not result.is_succeeded() else 'No results'}")
        
        # 方法3：直接 FETCH 边
        print(f"\n[Method 3] Fetching edges directly...")
        query3 = f'''
        FETCH PROP ON contains "{repo_vid}"->*
        YIELD properties(edge) as props;
        '''
        result = session.execute(query3)
        if result.is_succeeded():
            print(f"[OK] Method 3: Found {result.row_size()} edges")
            if result.row_size() > 0:
                # 显示前几个
                keys = result.keys()
                for idx in range(min(3, result.row_size())):
                    row = result.row_values(idx)
                    print(f"   Edge {idx+1}: {row}")
        else:
            print(f"[FAIL] Method 3 failed: {result.error_msg()}")
        
        # 方法4：检查边类型
        print(f"\n[Method 4] Checking edge types...")
        query4 = f'''
        MATCH (repo)-[e]->(target)
        WHERE id(repo) == "{repo_vid}"
        RETURN type(e) as edge_type, count(*) as count;
        '''
        result = session.execute(query4)
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            print(f"[OK] Method 4: Edge types:")
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
            verify_contains_edges(repo_id)
        except ValueError:
            print(f"Error: Invalid repo_id")
            sys.exit(1)
    else:
        print("Usage: python verify_contains_edges.py [repo_id]")
        sys.exit(1)
