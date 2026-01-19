"""
修复脚本：为已存在的文件节点批量创建 contains 边
"""

import os
import sys
from pathlib import Path
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from datetime import datetime


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


def fix_contains_edges(repo_id: int):
    """为指定仓库的文件节点批量创建 contains 边"""
    # 先加载 .env 文件
    load_env_file()
    
    print("=" * 60)
    print(f"Fixing contains edges for repository {repo_id}")
    print("=" * 60)
    print()
    
    # 从环境变量获取配置
    nebula_hosts_str = os.getenv('NEBULA_HOSTS', '127.0.0.1:9669')
    nebula_user = os.getenv('NEBULA_USER', 'root')
    nebula_password = os.getenv('NEBULA_PASSWORD', 'password')
    space = "multikb_knowledge"
    repo_vid = f"code_repository_{repo_id}"
    
    # 解析 hosts 格式
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
        print(f"[Step 1] Checking repository node: {repo_vid}")
        check_repo_nGQL = f'FETCH PROP ON code_repository "{repo_vid}" YIELD properties(vertex) as props;'
        result = session.execute(check_repo_nGQL)
        if not result.is_succeeded() or result.row_size() == 0:
            print(f"[FAIL] Repository node does not exist")
            session.release()
            return
        
        row = result.row_values(0)
        keys = result.keys()
        props = {}
        for i, col_name in enumerate(keys):
            if col_name == 'props':
                props_map = row[i].as_map()
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
                        props[k] = str(v)
        
        print(f"[OK] Repository node exists: {props.get('repo_name', 'N/A')}")
        print()
        
        # 2. 查找所有没有 contains 边的文件节点（通过 repository_id 属性匹配）
        print(f"[Step 2] Finding orphan file nodes (no contains edge)")
        find_orphan_files_nGQL = f'''
        MATCH (file:code_file)
        WHERE file.repository_id == {repo_id}
        AND NOT (file)<-[:contains]-()
        RETURN id(file) as vid, file.file_path as file_path
        LIMIT 1000;
        '''
        result = session.execute(find_orphan_files_nGQL)
        
        if not result.is_succeeded():
            print(f"[FAIL] Query failed: {result.error_msg()}")
            session.release()
            return
        
        orphan_files = []
        if result.row_size() > 0:
            keys = result.keys()
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                vid = None
                file_path = None
                for i, col_name in enumerate(keys):
                    if col_name == 'vid':
                        vid = str(row[i])
                    elif col_name == 'file_path':
                        file_path = row[i].as_string() if hasattr(row[i], 'as_string') else str(row[i])
                if vid:
                    orphan_files.append((vid, file_path))
        
        print(f"[OK] Found {len(orphan_files)} orphan file nodes")
        if len(orphan_files) == 0:
            print("[INFO] No orphan files to fix")
            session.release()
            return
        
        print(f"[INFO] Will create contains edges for {len(orphan_files)} files")
        print()
        
        # 3. 批量创建 contains 边
        print(f"[Step 3] Creating contains edges...")
        created_count = 0
        failed_count = 0
        created_at = int(datetime.now().timestamp())
        
        # 每批处理 100 个文件
        batch_size = 100
        for batch_start in range(0, len(orphan_files), batch_size):
            batch = orphan_files[batch_start:batch_start + batch_size]
            
            # 构建批量插入语句
            edge_values = []
            for vid, file_path in batch:
                # 转义 VID 中的特殊字符
                vid_escaped = vid.replace('"', '\\"')
                edge_values.append(f'"{repo_vid}" -> "{vid_escaped}":("repository", 0, 0, {created_at})')
            
            # 构建批量 INSERT EDGE 语句
            batch_nGQL = (
                f'INSERT EDGE contains('
                f'container_type, start_line, end_line, created_at'
                f') VALUES {", ".join(edge_values)};'
            )
            
            try:
                result = session.execute(batch_nGQL)
                if result.is_succeeded():
                    created_count += len(batch)
                    print(f"[OK] Created {created_count}/{len(orphan_files)} contains edges")
                else:
                    failed_count += len(batch)
                    print(f"[FAIL] Batch failed: {result.error_msg()}")
                    # 如果批量失败，尝试单个创建
                    print(f"[INFO] Trying to create edges one by one...")
                    for vid, file_path in batch:
                        try:
                            single_nGQL = (
                                f'INSERT EDGE contains('
                                f'container_type, start_line, end_line, created_at'
                                f') VALUES "{repo_vid}" -> "{vid}":("repository", 0, 0, {created_at});'
                            )
                            single_result = session.execute(single_nGQL)
                            if single_result.is_succeeded():
                                created_count += 1
                                failed_count -= 1
                            else:
                                print(f"[FAIL] Failed to create edge for {file_path}: {single_result.error_msg()}")
                        except Exception as e:
                            print(f"[FAIL] Exception creating edge for {file_path}: {e}")
            except Exception as e:
                failed_count += len(batch)
                print(f"[FAIL] Batch exception: {e}")
                import traceback
                traceback.print_exc()
        
        print()
        print(f"[Step 4] Summary:")
        print(f"   Created: {created_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total: {len(orphan_files)}")
        print()
        
        # 4. 验证修复结果
        print(f"[Step 5] Verifying fix...")
        verify_nGQL = f'''
        MATCH (repo:code_repository)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(file) as file_count;
        '''
        result = session.execute(verify_nGQL)
        if result.is_succeeded() and result.row_size() > 0:
            row = result.row_values(0)
            keys = result.keys()
            for i, col_name in enumerate(keys):
                if col_name == 'file_count':
                    file_count = row[i].as_int()
                    print(f"[OK] Repository now has {file_count} files connected via contains edges")
        
        session.release()
        print()
        print("=" * 60)
        print("Fix completed")
        print("=" * 60)
        
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection_pool.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        try:
            repo_id = int(sys.argv[1])
            fix_contains_edges(repo_id)
        except ValueError:
            print(f"Error: Invalid repo_id: {sys.argv[1]}")
            print("Usage: python fix_contains_edges.py [repo_id]")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("Please specify repo_id")
        print("Usage: python fix_contains_edges.py [repo_id]")
        sys.exit(1)
