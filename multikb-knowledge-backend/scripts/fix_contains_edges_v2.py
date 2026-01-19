"""
修复脚本：为已存在的文件节点批量创建 contains 边（版本2）
通过检查文件节点的 repository_id 属性来匹配
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
        
        print(f"[OK] Repository node exists")
        print()
        
        # 2. 查找所有文件节点，检查它们的 repository_id 属性
        print(f"[Step 2] Finding file nodes with repository_id == {repo_id}")
        
        # 方法1：通过 repository_id 属性查找
        find_files_nGQL = f'''
        MATCH (file:code_file)
        WHERE file.repository_id == {repo_id}
        RETURN id(file) as vid, file.file_path as file_path, file.repository_id as repo_id
        LIMIT 1000;
        '''
        result = session.execute(find_files_nGQL)
        
        files_by_repo_id = []
        if result.is_succeeded() and result.row_size() > 0:
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
                    files_by_repo_id.append((vid, file_path))
        
        print(f"[OK] Found {len(files_by_repo_id)} files with repository_id == {repo_id}")
        
        # 方法2：查找所有没有 contains 边的文件节点
        print(f"[Step 3] Finding all orphan file nodes (no contains edge)")
        find_orphan_nGQL = '''
        MATCH (file:code_file)
        WHERE NOT (file)<-[:contains]-()
        RETURN id(file) as vid, file.file_path as file_path, file.repository_id as repo_id
        LIMIT 2000;
        '''
        result = session.execute(find_orphan_nGQL)
        
        orphan_files = []
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                vid = None
                file_path = None
                repo_id_from_file = None
                for i, col_name in enumerate(keys):
                    if col_name == 'vid':
                        vid = str(row[i])
                    elif col_name == 'file_path':
                        try:
                            file_path = row[i].as_string() if hasattr(row[i], 'as_string') else str(row[i])
                        except:
                            file_path = None
                    elif col_name == 'repo_id':
                        try:
                            if hasattr(row[i], 'as_int'):
                                repo_id_from_file = row[i].as_int()
                            elif hasattr(row[i], 'is_null') and row[i].is_null():
                                repo_id_from_file = None
                            else:
                                repo_id_from_file = None
                        except:
                            repo_id_from_file = None
                
                # 如果文件的 repository_id 匹配，或者是 None（可能是旧数据）
                if vid and (repo_id_from_file == repo_id or repo_id_from_file is None):
                    orphan_files.append((vid, file_path))
        
        print(f"[OK] Found {len(orphan_files)} orphan file nodes (total, may include other repos)")
        print()
        
        # 3. 优先使用通过 repository_id 找到的文件
        files_to_fix = files_by_repo_id if files_by_repo_id else orphan_files[:1000]  # 限制数量
        
        if len(files_to_fix) == 0:
            print("[INFO] No files to fix")
            session.release()
            return
        
        print(f"[Step 4] Will create contains edges for {len(files_to_fix)} files")
        print()
        
        # 4. 检查哪些文件已经有 contains 边
        print(f"[Step 5] Checking which files already have contains edges...")
        files_with_edge = set()
        check_edges_nGQL = f'''
        MATCH (repo:code_repository)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN id(file) as vid
        LIMIT 5000;
        '''
        result = session.execute(check_edges_nGQL)
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                for i, col_name in enumerate(keys):
                    if col_name == 'vid':
                        vid = str(row[i])
                        files_with_edge.add(vid)
        
        print(f"[OK] Found {len(files_with_edge)} files that already have contains edges")
        
        # 过滤出需要创建边的文件
        files_to_create = [(vid, path) for vid, path in files_to_fix if vid not in files_with_edge]
        print(f"[OK] Need to create contains edges for {len(files_to_create)} files")
        print()
        
        if len(files_to_create) == 0:
            print("[INFO] All files already have contains edges")
            session.release()
            return
        
        # 5. 批量创建 contains 边
        print(f"[Step 6] Creating contains edges...")
        created_count = 0
        failed_count = 0
        created_at = int(datetime.now().timestamp())
        
        # 每批处理 50 个文件（避免语句过长）
        batch_size = 50
        for batch_start in range(0, len(files_to_create), batch_size):
            batch = files_to_create[batch_start:batch_start + batch_size]
            
            # 逐个创建（更可靠）
            for vid, file_path in batch:
                try:
                    # 转义 VID
                    vid_escaped = vid.replace('"', '\\"')
                    single_nGQL = (
                        f'INSERT EDGE contains('
                        f'container_type, start_line, end_line, created_at'
                        f') VALUES "{repo_vid}" -> "{vid_escaped}":("repository", 0, 0, {created_at});'
                    )
                    result = session.execute(single_nGQL)
                    if result.is_succeeded():
                        created_count += 1
                        if created_count % 100 == 0:
                            print(f"[OK] Created {created_count}/{len(files_to_create)} contains edges")
                    else:
                        failed_count += 1
                        if failed_count <= 10:
                            print(f"[FAIL] Failed to create edge for {file_path}: {result.error_msg()}")
                except Exception as e:
                    failed_count += 1
                    if failed_count <= 10:
                        print(f"[FAIL] Exception creating edge for {file_path}: {e}")
        
        print()
        print(f"[Step 7] Summary:")
        print(f"   Created: {created_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total: {len(files_to_create)}")
        print()
        
        # 6. 验证修复结果
        print(f"[Step 8] Verifying fix...")
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
            print("Usage: python fix_contains_edges_v2.py [repo_id]")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("Please specify repo_id")
        print("Usage: python fix_contains_edges_v2.py [repo_id]")
        sys.exit(1)
