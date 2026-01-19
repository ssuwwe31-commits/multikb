"""
检查节点和边的标签
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


def check_labels(repo_id: int):
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
        
        # 检查仓库节点的标签
        print(f"[Check 1] Checking repository node labels...")
        query1 = f'''
        FETCH PROP ON code_repository "{repo_vid}"
        YIELD labels(vertex) as tags;
        '''
        result = session.execute(query1)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'tags':
                    tags = row[i]
                    print(f"[OK] Repository tags: {tags}")
        
        # 检查文件节点的标签（通过 GO 查询找到的文件）
        print(f"\n[Check 2] Checking file node labels (via GO query)...")
        query2 = f'''
        GO FROM "{repo_vid}" OVER contains
        YIELD dst(edge) as file_vid
        LIMIT 5;
        '''
        result = session.execute(query2)
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            file_vids = []
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                for i, col_name in enumerate(keys):
                    if col_name == 'file_vid':
                        file_vids.append(str(row[i]))
            
            print(f"[OK] Found {len(file_vids)} file VIDs via GO query")
            if file_vids:
                # 检查第一个文件的标签
                first_vid = file_vids[0]
                query3 = f'''
                FETCH PROP ON code_file "{first_vid}"
                YIELD labels(vertex) as tags;
                '''
                result = session.execute(query3)
                if result.is_succeeded() and result.row_size() > 0:
                    row = result.row_values(0)
                    keys = result.keys()
                    for i, col_name in enumerate(keys):
                        if col_name == 'tags':
                            tags = row[i]
                            print(f"[OK] File tags (first file): {tags}")
        
        # 检查 contains 边的属性
        print(f"\n[Check 3] Checking contains edge properties...")
        query4 = f'''
        GO FROM "{repo_vid}" OVER contains
        YIELD properties(edge) as props, dst(edge) as file_vid
        LIMIT 3;
        '''
        result = session.execute(query4)
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            print(f"[OK] Contains edge properties (first 3):")
            for idx in range(min(3, result.row_size())):
                row = result.row_values(idx)
                props = None
                file_vid = None
                for i, col_name in enumerate(keys):
                    if col_name == 'props':
                        props_map = row[i].as_map()
                        props = {}
                        for k, v in props_map.items():
                            try:
                                if hasattr(v, 'as_string'):
                                    props[k] = v.as_string()
                                elif hasattr(v, 'as_int'):
                                    props[k] = v.as_int()
                                else:
                                    props[k] = str(v)
                            except:
                                props[k] = str(v)
                    elif col_name == 'file_vid':
                        file_vid = str(row[i])
                print(f"   Edge {idx+1}: file_vid={file_vid}, props={props}")
        
        # 测试不同的 MATCH 查询
        print(f"\n[Check 4] Testing different MATCH queries...")
        
        # 测试1：不指定标签
        query5 = f'''
        MATCH (repo)-[:contains]->(file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(file) as file_count;
        '''
        result = session.execute(query5)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'file_count':
                    count = row[i].as_int()
                    print(f"[OK] MATCH without labels: {count} files")
        
        # 测试2：只指定文件标签
        query6 = f'''
        MATCH (repo)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(file) as file_count;
        '''
        result = session.execute(query6)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'file_count':
                    count = row[i].as_int()
                    print(f"[OK] MATCH with file label: {count} files")
        
        # 测试3：只指定仓库标签
        query7 = f'''
        MATCH (repo:code_repository)-[:contains]->(file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(file) as file_count;
        '''
        result = session.execute(query7)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'file_count':
                    count = row[i].as_int()
                    print(f"[OK] MATCH with repo label: {count} files")
        
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
            check_labels(repo_id)
        except ValueError:
            print(f"Error: Invalid repo_id")
            sys.exit(1)
    else:
        print("Usage: python check_labels.py [repo_id]")
        sys.exit(1)
