"""
智能修复脚本：从 MySQL 获取文件列表，计算 VID，然后创建 contains 边
"""

import os
import sys
import hashlib
from pathlib import Path
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from datetime import datetime
import json


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


def generate_file_vid(repository_id: int, file_path: str) -> str:
    """生成文件节点的 VID（与代码中的逻辑一致）"""
    vid_key = f"{repository_id}:{file_path}"
    vid_hash = hashlib.md5(vid_key.encode('utf-8')).hexdigest()[:16]
    return f"code_file_{vid_hash}"


def get_files_from_mysql(repo_id: int):
    """从 MySQL 缓存中获取文件列表"""
    try:
        import pymysql
        
        # 从环境变量获取 MySQL 配置
        mysql_host = os.getenv('MYSQL_HOST', '127.0.0.1')
        mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
        mysql_user = os.getenv('MYSQL_USER', 'root')
        mysql_password = os.getenv('MYSQL_PASSWORD', 'password')
        mysql_database = os.getenv('MYSQL_DATABASE', 'multikb_knowledge')
        
        conn = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database,
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # 从缓存中获取文件列表
        cursor.execute("""
            SELECT cache_data 
            FROM code_analysis_cache 
            WHERE repository_id = %s 
            AND cache_type = 'structure' 
            AND cache_key = 'full'
            ORDER BY created_at DESC 
            LIMIT 1
        """, (repo_id,))
        
        result = cursor.fetchone()
        if result and result[0]:
            cache_data = json.loads(result[0])
            files = cache_data.get('files', [])
            cursor.close()
            conn.close()
            return files
        
        cursor.close()
        conn.close()
        return []
    except Exception as e:
        print(f"[WARN] Failed to get files from MySQL: {e}")
        return []


def find_orphan_files_from_nebula(session, repo_id: int, repo_vid: str, space: str):
    """从 NebulaGraph 查找孤立文件节点（通过 repository_id 属性匹配）"""
    print(f"[INFO] Finding orphan files by repository_id == {repo_id}...")
    
    # 方法1：通过 repository_id 属性查找所有文件
    find_files_nGQL = f'''
    MATCH (file:code_file)
    WHERE file.repository_id == {repo_id}
    AND NOT (file)<-[:contains]-()
    RETURN id(file) as vid, file.file_path as file_path
    LIMIT 2000;
    '''
    
    result = session.execute(find_files_nGQL)
    orphan_files = []
    
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
                    try:
                        if hasattr(row[i], 'as_string'):
                            file_path = row[i].as_string()
                        elif hasattr(row[i], 'is_null') and not row[i].is_null():
                            file_path = str(row[i])
                        else:
                            file_path = None
                    except:
                        file_path = None
            if vid:
                orphan_files.append((vid, file_path or 'unknown'))
    
    if orphan_files:
        print(f"[OK] Found {len(orphan_files)} orphan files by repository_id")
        return orphan_files
    
    # 方法2：如果方法1没找到，查找所有孤立文件（可能 repository_id 属性不存在）
    print(f"[INFO] No files found by repository_id, trying to find all orphan files...")
    find_all_orphan_nGQL = '''
    MATCH (file:code_file)
    WHERE NOT (file)<-[:contains]-()
    RETURN id(file) as vid, file.file_path as file_path, file.repository_id as repo_id
    LIMIT 2000;
    '''
    
    result = session.execute(find_all_orphan_nGQL)
    all_orphan_files = []
    
    if result.is_succeeded() and result.row_size() > 0:
        keys = result.keys()
        for idx in range(result.row_size()):
            row = result.row_values(idx)
            vid = None
            file_path = None
            file_repo_id = None
            for i, col_name in enumerate(keys):
                if col_name == 'vid':
                    vid = str(row[i])
                elif col_name == 'file_path':
                    try:
                        if hasattr(row[i], 'as_string'):
                            file_path = row[i].as_string()
                        else:
                            file_path = None
                    except:
                        file_path = None
                elif col_name == 'repo_id':
                    try:
                        if hasattr(row[i], 'as_int'):
                            file_repo_id = row[i].as_int()
                        elif hasattr(row[i], 'is_null') and not row[i].is_null():
                            try:
                                file_repo_id = int(str(row[i]))
                            except:
                                file_repo_id = None
                        else:
                            file_repo_id = None
                    except:
                        file_repo_id = None
            
            # 如果 repository_id 匹配，或者为 None（可能是旧数据，需要手动匹配）
            if vid and (file_repo_id == repo_id or file_repo_id is None):
                all_orphan_files.append((vid, file_path or 'unknown'))
    
    if all_orphan_files:
        print(f"[OK] Found {len(all_orphan_files)} orphan files (may include other repos)")
        # 如果数量合理（小于1000），假设都属于这个仓库
        if len(all_orphan_files) <= 1000:
            return all_orphan_files
        else:
            print(f"[WARN] Too many orphan files ({len(all_orphan_files)}), please specify repo_id more carefully")
            return []
    
    return []


def fix_contains_edges(repo_id: int):
    """为指定仓库的文件节点批量创建 contains 边"""
    # 先加载 .env 文件
    load_env_file()
    
    print("=" * 60)
    print(f"Fixing contains edges for repository {repo_id}")
    print("=" * 60)
    print()
    
    # 先连接 NebulaGraph，然后查找孤立文件
    # MySQL 缓存作为备选方案
    
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
        print(f"[Step 2] Checking repository node: {repo_vid}")
        check_repo_nGQL = f'FETCH PROP ON code_repository "{repo_vid}" YIELD properties(vertex) as props;'
        result = session.execute(check_repo_nGQL)
        if not result.is_succeeded() or result.row_size() == 0:
            print(f"[FAIL] Repository node does not exist")
            session.release()
            return
        
        print(f"[OK] Repository node exists")
        print()
        
        # 2. 从 NebulaGraph 查找孤立文件节点
        print(f"[Step 3] Finding orphan file nodes from NebulaGraph...")
        files_to_fix = find_orphan_files_from_nebula(session, repo_id, repo_vid, space)
        
        if not files_to_fix:
            # 尝试从 MySQL 缓存获取文件列表
            print(f"[Step 3b] Trying to get file list from MySQL cache...")
            files = get_files_from_mysql(repo_id)
            if files:
                print(f"[OK] Found {len(files)} files in MySQL cache, calculating VIDs...")
                file_vids = []
                for file_data in files:
                    file_path = file_data.get('file_path', '')
                    if file_path:
                        vid = generate_file_vid(repo_id, file_path)
                        file_vids.append((vid, file_path))
                
                # 检查这些文件节点是否存在且没有 contains 边
                for vid, file_path in file_vids:
                    check_edge_nGQL = f'''
                    MATCH (repo:code_repository)-[e:contains]->(file:code_file)
                    WHERE id(repo) == "{repo_vid}" AND id(file) == "{vid}"
                    RETURN count(e) as edge_count;
                    '''
                    edge_result = session.execute(check_edge_nGQL)
                    has_edge = False
                    if edge_result.is_succeeded() and edge_result.row_size() > 0:
                        row = edge_result.row_values(0)
                        keys = edge_result.keys()
                        for i, col_name in enumerate(keys):
                            if col_name == 'edge_count':
                                count = row[i].as_int()
                                has_edge = (count > 0)
                    
                    if not has_edge:
                        files_to_fix.append((vid, file_path))
        
        print(f"[OK] Found {len(files_to_fix)} files that need contains edges")
        print()
        
        if len(files_to_fix) == 0:
            print("[INFO] All files already have contains edges")
            session.release()
            return
        
        # 3. 批量创建 contains 边
        print(f"[Step 4] Creating contains edges...")
        created_count = 0
        failed_count = 0
        created_at = int(datetime.now().timestamp())
        
        # 每批处理 50 个文件
        batch_size = 50
        for batch_start in range(0, len(files_to_fix), batch_size):
            batch = files_to_fix[batch_start:batch_start + batch_size]
            
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
                            print(f"[OK] Created {created_count}/{len(files_to_fix)} contains edges")
                    else:
                        failed_count += 1
                        if failed_count <= 10:
                            error_msg = result.error_msg()
                            # 如果是已存在的错误，不算失败
                            if "existed" in error_msg.lower() or "Existed" in error_msg:
                                created_count += 1
                                failed_count -= 1
                            else:
                                print(f"[FAIL] Failed to create edge for {file_path}: {error_msg}")
                except Exception as e:
                    failed_count += 1
                    if failed_count <= 10:
                        print(f"[FAIL] Exception creating edge for {file_path}: {e}")
        
        print()
        print(f"[Step 6] Summary:")
        print(f"   Created: {created_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total: {len(files_to_fix)}")
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
            print("Usage: python fix_contains_edges_smart.py [repo_id]")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("Please specify repo_id")
        print("Usage: python fix_contains_edges_smart.py [repo_id]")
        sys.exit(1)
