"""
修复所有孤立文件节点：为所有没有 contains 边的文件节点创建边
注意：这个脚本会为所有孤立文件创建边到指定的仓库，请确认这些文件确实属于该仓库
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


def fix_all_orphan_files(repo_id: int, limit: int = 1000):
    """为所有孤立文件节点创建 contains 边到指定仓库"""
    # 先加载 .env 文件
    load_env_file()
    
    print("=" * 60)
    print(f"Fixing ALL orphan files for repository {repo_id}")
    print(f"WARNING: This will create contains edges for up to {limit} orphan files")
    print("=" * 60)
    print()
    
    # 从环境变量获取 NebulaGraph 配置
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
        
        # 2. 查找所有孤立文件节点
        print(f"[Step 2] Finding all orphan file nodes (limit: {limit})...")
        find_orphan_nGQL = f'''
        MATCH (file:code_file)
        WHERE NOT (file)<-[:contains]-()
        RETURN id(file) as vid
        LIMIT {limit};
        '''
        
        result = session.execute(find_orphan_nGQL)
        orphan_files = []
        
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                for i, col_name in enumerate(keys):
                    if col_name == 'vid':
                        vid = str(row[i])
                        orphan_files.append(vid)
        
        print(f"[OK] Found {len(orphan_files)} orphan file nodes")
        print()
        
        if len(orphan_files) == 0:
            print("[INFO] No orphan files to fix")
            session.release()
            return
        
        # 3. 检查哪些文件已经有 contains 边（双重检查）
        print(f"[Step 3] Double-checking which files need contains edges...")
        files_to_fix = []
        batch_size = 100
        
        for batch_start in range(0, len(orphan_files), batch_size):
            batch = orphan_files[batch_start:batch_start + batch_size]
            vid_list = [f'"{vid}"' for vid in batch]
            vid_list_str = ', '.join(vid_list)
            
            # 检查这些文件是否已经有 contains 边
            check_edges_nGQL = f'''
            MATCH (repo:code_repository)-[e:contains]->(file:code_file)
            WHERE id(repo) == "{repo_vid}" AND id(file) IN [{vid_list_str}]
            RETURN id(file) as vid;
            '''
            result = session.execute(check_edges_nGQL)
            
            files_with_edge = set()
            if result.is_succeeded() and result.row_size() > 0:
                keys = result.keys()
                for idx in range(result.row_size()):
                    row = result.row_values(idx)
                    for i, col_name in enumerate(keys):
                        if col_name == 'vid':
                            files_with_edge.add(str(row[i]))
            
            # 添加没有边的文件
            for vid in batch:
                if vid not in files_with_edge:
                    files_to_fix.append(vid)
        
        print(f"[OK] Need to create contains edges for {len(files_to_fix)} files")
        print()
        
        if len(files_to_fix) == 0:
            print("[INFO] All files already have contains edges")
            session.release()
            return
        
        # 4. 批量创建 contains 边
        print(f"[Step 4] Creating contains edges...")
        created_count = 0
        failed_count = 0
        created_at = int(datetime.now().timestamp())
        
        # 每批处理 50 个文件
        batch_size = 50
        for batch_start in range(0, len(files_to_fix), batch_size):
            batch = files_to_fix[batch_start:batch_start + batch_size]
            
            # 逐个创建（更可靠）
            for vid in batch:
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
                            print(f"[OK] Created {created_count}/{len(files_to_fix)} contains edges")
                    else:
                        error_msg = result.error_msg()
                        # 如果是已存在的错误，不算失败
                        if "existed" in error_msg.lower() or "Existed" in error_msg:
                            created_count += 1
                        else:
                            failed_count += 1
                            if failed_count <= 10:
                                print(f"[FAIL] Failed to create edge for {vid}: {error_msg}")
                except Exception as e:
                    failed_count += 1
                    if failed_count <= 10:
                        print(f"[FAIL] Exception creating edge for {vid}: {e}")
        
        print()
        print(f"[Step 5] Summary:")
        print(f"   Created: {created_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total: {len(files_to_fix)}")
        print()
        
        # 5. 验证修复结果
        print(f"[Step 6] Verifying fix...")
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
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
            print(f"WARNING: This will create contains edges for up to {limit} orphan files")
            print("Press Ctrl+C to cancel, or wait 3 seconds to continue...")
            import time
            time.sleep(3)
            fix_all_orphan_files(repo_id, limit)
        except ValueError:
            print(f"Error: Invalid repo_id: {sys.argv[1]}")
            print("Usage: python fix_all_orphan_files.py [repo_id] [limit]")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n[CANCELLED] Operation cancelled by user")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("Please specify repo_id")
        print("Usage: python fix_all_orphan_files.py [repo_id] [limit]")
        sys.exit(1)
