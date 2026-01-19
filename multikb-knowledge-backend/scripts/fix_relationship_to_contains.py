"""
修复脚本：将错误的 relationship 边转换为 contains 边
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


def fix_relationship_to_contains(repo_id: int):
    """将 relationship 边转换为 contains 边"""
    load_env_file()
    
    print("=" * 60)
    print(f"Fixing relationship edges to contains edges for repository {repo_id}")
    print("=" * 60)
    print()
    
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
        
        # 1. 查找所有 relationship 边
        print(f"[Step 1] Finding relationship edges from {repo_vid}...")
        find_relationship_nGQL = f'''
        MATCH (repo)-[e:relationship]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN id(file) as file_vid
        LIMIT 2000;
        '''
        
        result = session.execute(find_relationship_nGQL)
        file_vids = []
        
        if result.is_succeeded() and result.row_size() > 0:
            keys = result.keys()
            for idx in range(result.row_size()):
                row = result.row_values(idx)
                for i, col_name in enumerate(keys):
                    if col_name == 'file_vid':
                        vid = str(row[i])
                        file_vids.append(vid)
        
        print(f"[OK] Found {len(file_vids)} files connected via relationship edges")
        print()
        
        if len(file_vids) == 0:
            print("[INFO] No relationship edges to fix")
            session.release()
            return
        
        # 2. 检查哪些文件已经有 contains 边
        print(f"[Step 2] Checking which files already have contains edges...")
        files_with_contains = set()
        batch_size = 100
        
        for batch_start in range(0, len(file_vids), batch_size):
            batch = file_vids[batch_start:batch_start + batch_size]
            vid_list = [f'"{vid}"' for vid in batch]
            vid_list_str = ', '.join(vid_list)
            
            check_contains_nGQL = f'''
            MATCH (repo:code_repository)-[e:contains]->(file:code_file)
            WHERE id(repo) == "{repo_vid}" AND id(file) IN [{vid_list_str}]
            RETURN id(file) as vid;
            '''
            result = session.execute(check_contains_nGQL)
            
            if result.is_succeeded() and result.row_size() > 0:
                keys = result.keys()
                for idx in range(result.row_size()):
                    row = result.row_values(idx)
                    for i, col_name in enumerate(keys):
                        if col_name == 'vid':
                            files_with_contains.add(str(row[i]))
        
        files_to_fix = [vid for vid in file_vids if vid not in files_with_contains]
        print(f"[OK] Need to create contains edges for {len(files_to_fix)} files")
        print()
        
        if len(files_to_fix) == 0:
            print("[INFO] All files already have contains edges")
            # 删除 relationship 边
            print(f"[Step 3] Deleting relationship edges...")
            delete_nGQL = f'''
            MATCH (repo)-[e:relationship]->(file:code_file)
            WHERE id(repo) == "{repo_vid}"
            DELETE e;
            '''
            result = session.execute(delete_nGQL)
            if result.is_succeeded():
                print(f"[OK] Deleted relationship edges")
            session.release()
            return
        
        # 3. 创建 contains 边
        print(f"[Step 3] Creating contains edges...")
        created_count = 0
        failed_count = 0
        created_at = int(datetime.now().timestamp())
        
        for vid in files_to_fix:
            try:
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
                    if "existed" in error_msg.lower():
                        created_count += 1
                    else:
                        failed_count += 1
                        if failed_count <= 10:
                            print(f"[FAIL] Failed: {error_msg}")
            except Exception as e:
                failed_count += 1
                if failed_count <= 10:
                    print(f"[FAIL] Exception: {e}")
        
        print()
        print(f"[Step 4] Summary:")
        print(f"   Created: {created_count}")
        print(f"   Failed: {failed_count}")
        print()
        
        # 4. 删除 relationship 边（逐个删除，更可靠）
        print(f"[Step 5] Deleting relationship edges...")
        deleted_count = 0
        for vid in file_vids:
            try:
                vid_escaped = vid.replace('"', '\\"')
                delete_nGQL = f'''
                MATCH (repo)-[e:relationship]->(file:code_file)
                WHERE id(repo) == "{repo_vid}" AND id(file) == "{vid_escaped}"
                DELETE e;
                '''
                result = session.execute(delete_nGQL)
                if result.is_succeeded():
                    deleted_count += 1
                    if deleted_count % 100 == 0:
                        print(f"[OK] Deleted {deleted_count}/{len(file_vids)} relationship edges")
            except Exception as e:
                if deleted_count <= 10:
                    print(f"[FAIL] Failed to delete relationship edge: {e}")
        
        print(f"[OK] Deleted {deleted_count} relationship edges")
        print()
        
        # 5. 验证
        print(f"[Step 6] Verifying...")
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
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection_pool.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            repo_id = int(sys.argv[1])
            fix_relationship_to_contains(repo_id)
        except ValueError:
            print(f"Error: Invalid repo_id")
            sys.exit(1)
    else:
        print("Usage: python fix_relationship_to_contains.py [repo_id]")
        sys.exit(1)
