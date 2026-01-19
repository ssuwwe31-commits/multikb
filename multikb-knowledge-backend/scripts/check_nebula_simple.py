"""
直接检查 NebulaGraph 中的数据（不依赖项目模块）
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


def check_repository_data(repo_id: int):
    """检查指定仓库的数据"""
    # 先加载 .env 文件
    load_env_file()
    
    print("=" * 60)
    print(f"Checking repository {repo_id} data")
    print("=" * 60)
    print()
    
    # 从环境变量获取配置
    nebula_hosts_str = os.getenv('NEBULA_HOSTS', '127.0.0.1:9669')
    nebula_user = os.getenv('NEBULA_USER', 'root')
    nebula_password = os.getenv('NEBULA_PASSWORD', 'password')
    space = "multikb_knowledge"
    repo_vid = f"code_repository_{repo_id}"
    
    # 解析 hosts 格式：支持 "host:port" 或 "host1:port1,host2:port2"
    if ':' in nebula_hosts_str:
        if ',' in nebula_hosts_str:
            # 多个 hosts
            nebula_hosts = []
            for host_str in nebula_hosts_str.split(','):
                host_parts = host_str.strip().split(':')
                if len(host_parts) == 2:
                    nebula_hosts.append((host_parts[0].strip(), int(host_parts[1].strip())))
        else:
            # 单个 host
            host_parts = nebula_hosts_str.split(':')
            nebula_host = host_parts[0]
            nebula_port = int(host_parts[1])
            nebula_hosts = [(nebula_host, nebula_port)]
    else:
        nebula_hosts = [('127.0.0.1', 9669)]
    
    print(f"Connection: {nebula_hosts}, User: {nebula_user}, Space: {space}")
    print()
    
    # 创建连接池
    config = Config()
    config.max_connection_pool_size = 10
    connection_pool = ConnectionPool()
    
    try:
        # 初始化连接池
        if not connection_pool.init(nebula_hosts, config):
            print("[FAIL] Failed to initialize connection pool")
            return
        
        # 获取会话
        session = connection_pool.get_session(nebula_user, nebula_password)
        
        # 切换到正确的 space
        result = session.execute(f"USE {space};")
        if not result.is_succeeded():
            print(f"[FAIL] Failed to switch to space: {result.error_msg()}")
            session.release()
            return
        
        # 1. 检查仓库节点是否存在
        print(f"[Check 1] Checking repository node: {repo_vid}")
        try:
            check_repo_nGQL = f'FETCH PROP ON code_repository "{repo_vid}" YIELD properties(vertex) as props;'
            result = session.execute(check_repo_nGQL)
            if result.is_succeeded() and result.row_size() > 0:
                row = result.row_values(0)
                # 获取列名
                keys = result.keys()
                props = {}
                for i, col_name in enumerate(keys):
                    if col_name == 'props':
                        props_map = row[i].as_map()
                        # 转换 map 值为字符串
                        for k, v in props_map.items():
                            try:
                                if hasattr(v, 'as_string'):
                                    props[k] = v.as_string()
                                elif hasattr(v, 'as_int'):
                                    props[k] = v.as_int()
                                elif hasattr(v, 'as_double'):
                                    props[k] = v.as_double()
                                else:
                                    props[k] = str(v)
                            except Exception:
                                # 如果转换失败，直接转字符串
                                props[k] = str(v)
                
                print(f"[OK] Repository node exists")
                print(f"   repo_name: {props.get('repo_name', 'N/A')}")
                print(f"   repo_url: {props.get('repo_url', 'N/A')}")
                print(f"   total_files: {props.get('total_files', 'N/A')}")
                print(f"   total_lines: {props.get('total_lines', 'N/A')}")
            else:
                print(f"[FAIL] Repository node does not exist")
                if not result.is_succeeded():
                    print(f"   Error: {result.error_msg()}")
                session.release()
                return
        except Exception as e:
            print(f"[FAIL] Failed to check repository node: {e}")
            import traceback
            traceback.print_exc()
            session.release()
            return
        print()
        
        # 2. 检查文件节点数量（使用 GO 查询，更可靠）
        print(f"[Check 2] Checking file node count (via contains edge)")
        try:
            # 使用 GO 查询
            count_files_nGQL = f'''
            GO FROM "{repo_vid}" OVER contains
            YIELD dst(edge) as vid
            | YIELD count(*) as file_count;
            '''
            result = session.execute(count_files_nGQL)
            if result.is_succeeded() and result.row_size() > 0:
                row = result.row_values(0)
                keys = result.keys()
                for i, col_name in enumerate(keys):
                    if col_name == 'file_count':
                        file_count = row[i].as_int()
                        print(f"[OK] Found {file_count} file nodes (via contains edge)")
            else:
                print(f"[FAIL] Query failed or returned empty result")
                if not result.is_succeeded():
                    print(f"   Error: {result.error_msg()}")
        except Exception as e:
            print(f"[FAIL] Failed to check file node count: {e}")
            import traceback
            traceback.print_exc()
        print()
        
        # 3. 检查所有 code_file 节点（不通过边）
        print(f"[Check 3] Checking all code_file nodes (without edge)")
        try:
            count_all_files_nGQL = '''
            MATCH (file:code_file)
            RETURN count(file) as total_files;
            '''
            result = session.execute(count_all_files_nGQL)
            if result.is_succeeded() and result.row_size() > 0:
                row = result.row_values(0)
                keys = result.keys()
                for i, col_name in enumerate(keys):
                    if col_name == 'total_files':
                        total_files = row[i].as_int()
                        print(f"[OK] Total {total_files} code_file nodes in graph database")
            else:
                print(f"[FAIL] Query failed")
                if not result.is_succeeded():
                    print(f"   Error: {result.error_msg()}")
        except Exception as e:
            print(f"[FAIL] Failed to check all file nodes: {e}")
            import traceback
            traceback.print_exc()
        print()
        
        # 4. 列出前10个文件节点（使用 GO 查询，然后 FETCH 属性）
        print(f"[Check 4] Listing first 10 file nodes")
        try:
            # 先获取 VID
            list_vids_nGQL = f'''
            GO FROM "{repo_vid}" OVER contains
            YIELD dst(edge) as vid
            | LIMIT 10;
            '''
            result = session.execute(list_vids_nGQL)
            if result.is_succeeded() and result.row_size() > 0:
                keys = result.keys()
                file_vids = []
                for idx in range(result.row_size()):
                    row = result.row_values(idx)
                    for i, col_name in enumerate(keys):
                        if col_name == 'vid':
                            file_vids.append(str(row[i]))
                
                # 然后 FETCH 属性
                if file_vids:
                    vid_list_str = ', '.join([f'"{vid}"' for vid in file_vids])
                    fetch_nGQL = f'''
                    FETCH PROP ON code_file {vid_list_str}
                    YIELD id(vertex) as vid, properties(vertex) as props;
                    '''
                    fetch_result = session.execute(fetch_nGQL)
                    if fetch_result.is_succeeded() and fetch_result.row_size() > 0:
                        print(f"[OK] Found {fetch_result.row_size()} file nodes (first 10):")
                        fetch_keys = fetch_result.keys()
                        for idx in range(fetch_result.row_size()):
                            row = fetch_result.row_values(idx)
                            vid = None
                            props = {}
                            for i, col_name in enumerate(fetch_keys):
                                if col_name == 'vid':
                                    vid = str(row[i])
                                elif col_name == 'props':
                                    props_map = row[i].as_map()
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
                            print(f"   [{idx+1}] VID: {vid}")
                            print(f"       Path: {props.get('file_path', 'N/A')}")
                            print(f"       Language: {props.get('language', 'N/A')}")
            else:
                print(f"[FAIL] No file nodes found")
                if not result.is_succeeded():
                    print(f"   Error: {result.error_msg()}")
        except Exception as e:
            print(f"[FAIL] Failed to list file nodes: {e}")
            import traceback
            traceback.print_exc()
        print()
        
        # 5. 检查所有 code_repository 节点
        print(f"[Check 5] Checking all code_repository nodes")
        try:
            list_repos_nGQL = '''
            MATCH (repo:code_repository)
            RETURN id(repo) as vid, repo.repo_name as repo_name, repo.mysql_id as mysql_id
            LIMIT 20;
            '''
            result = session.execute(list_repos_nGQL)
            if result.is_succeeded() and result.row_size() > 0:
                print(f"[OK] Found {result.row_size()} repository nodes:")
                keys = result.keys()
                for idx in range(result.row_size()):
                    row = result.row_values(idx)
                    vid = None
                    repo_name = None
                    mysql_id = None
                    for i, col_name in enumerate(keys):
                        if col_name == 'vid':
                            vid = str(row[i])
                        elif col_name == 'repo_name':
                            repo_name = row[i].as_string() if hasattr(row[i], 'as_string') else str(row[i])
                        elif col_name == 'mysql_id':
                            mysql_id = row[i].as_int() if hasattr(row[i], 'as_int') else str(row[i])
                    print(f"   [{idx+1}] VID: {vid}, MySQL ID: {mysql_id}, Name: {repo_name}")
            else:
                print(f"[FAIL] No repository nodes found")
                if not result.is_succeeded():
                    print(f"   Error: {result.error_msg()}")
        except Exception as e:
            print(f"[FAIL] Failed to check repository nodes: {e}")
            import traceback
            traceback.print_exc()
        print()
        
        # 6. 检查是否有孤立文件节点（没有 contains 边）
        print(f"[Check 6] Checking orphan file nodes (no contains edge)")
        try:
            orphan_files_nGQL = '''
            MATCH (file:code_file)
            WHERE NOT (file)<-[:contains]-()
            RETURN count(file) as orphan_count
            LIMIT 1;
            '''
            result = session.execute(orphan_files_nGQL)
            if result.is_succeeded() and result.row_size() > 0:
                row = result.row_values(0)
                keys = result.keys()
                for i, col_name in enumerate(keys):
                    if col_name == 'orphan_count':
                        orphan_count = row[i].as_int()
                        if orphan_count > 0:
                            print(f"[WARN] Found {orphan_count} orphan file nodes (no contains edge)")
                        else:
                            print(f"[OK] No orphan file nodes")
            else:
                print(f"[FAIL] Query failed")
                if not result.is_succeeded():
                    print(f"   Error: {result.error_msg()}")
        except Exception as e:
            print(f"[FAIL] Failed to check orphan file nodes: {e}")
            import traceback
            traceback.print_exc()
        print()
        
        session.release()
        print("=" * 60)
        print("Check completed")
        print("=" * 60)
        
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection_pool.close()


if __name__ == "__main__":
    import sys
    
    print(f"Debug: sys.argv = {sys.argv}")
    print(f"Debug: len(sys.argv) = {len(sys.argv)}")
    
    if len(sys.argv) > 1:
        try:
            repo_id_str = sys.argv[1]
            print(f"Debug: repo_id_str = {repo_id_str}, type = {type(repo_id_str)}")
            repo_id = int(repo_id_str)
            print(f"Debug: repo_id = {repo_id}, type = {type(repo_id)}")
            print(f"Debug: Calling check_repository_data({repo_id})")
            check_repository_data(repo_id)
        except ValueError as e:
            print(f"Error: Invalid repo_id: {sys.argv[1]}")
            print(f"Error details: {e}")
            print(f"Usage: python check_nebula_simple.py [repo_id]")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("Please specify repo_id")
        print("Usage: python check_nebula_simple.py [repo_id]")
        sys.exit(1)
