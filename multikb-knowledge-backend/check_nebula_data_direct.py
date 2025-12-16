#!/usr/bin/env python3
"""
直接检查NebulaGraph中的数据
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
project_root = Path(__file__).parent
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

try:
    from nebula3.gclient.net import ConnectionPool
    from nebula3.Config import Config
except ImportError:
    print("[ERROR] 请先安装 nebula3-python: pip install nebula3-python")
    sys.exit(1)

kb_id = 4
space = f"kb_{kb_id}"

print("=" * 60)
print(f"检查 NebulaGraph 空间: {space}")
print("=" * 60)

config = get_nebula_config()
print(f"连接配置: {config}")

# 创建连接池
pool = ConnectionPool()
try:
    nebula_config = Config()
    nebula_config.max_connection_pool_size = 1
    nebula_config.timeout = 10000
    
    if not pool.init(config["hosts"], nebula_config):
        print("[ERROR] 连接池初始化失败")
        sys.exit(1)
    
    print("[OK] 连接池初始化成功")
    
    # 获取会话
    session = pool.get_session(config["user"], config["password"])
    if not session:
        print("[ERROR] 无法获取会话")
        sys.exit(1)
    
    print("[OK] 会话创建成功")
    
    # 切换到指定空间
    use_result = session.execute(f"USE {space};")
    if not use_result.is_succeeded():
        error_msg = use_result.error_msg()
        print(f"[ERROR] USE空间失败: {error_msg}")
        session.release()
        pool.close()
        sys.exit(1)
    
    print(f"[OK] 已切换到空间: {space}")
    
    # 先查询实体总数
    print("\n[步骤1] 查询实体总数...")
    count_query = "MATCH (n:entity) RETURN count(n) as total;"
    count_result = session.execute(count_query)
    if count_result.is_succeeded() and count_result.row_size() > 0:
        row = list(count_result)[0]
        row_values = row.values()
        if len(row_values) > 0:
            total_value = row_values[0]
            if hasattr(total_value, '_value'):
                inner = total_value._value
                if hasattr(inner, 'iVal'):
                    total = inner.iVal
                    print(f"实体总数: {total}")
                else:
                    print(f"实体总数（无法解析）: {total_value}")
    else:
        print("[WARN] 无法查询实体总数")
    
    # 查询前3个实体，使用FETCH PROP查看原始数据
    print("\n[步骤2] 查询前3个实体VID...")
    vid_list = []
    query_vids = "MATCH (n:entity) RETURN id(n) as vid LIMIT 3;"
    vid_result = session.execute(query_vids)
    
    if vid_result.is_succeeded():
        print(f"查询成功，行数: {vid_result.row_size()}")
        for i, row in enumerate(vid_result, 1):
            print(f"  处理第 {i} 行...")
            row_values = row.values()
            print(f"    行值数量: {len(row_values)}")
            if len(row_values) > 0:
                vid_value = row_values[0]
                print(f"    vid_value类型: {type(vid_value)}")
                print(f"    vid_value对象: {vid_value}")
                # 尝试获取vid字符串值
                if hasattr(vid_value, '_value'):
                    inner_value = vid_value._value
                    print(f"    inner_value类型: {type(inner_value)}")
                    print(f"    inner_value对象: {inner_value}")
                    # 尝试多种方式获取sVal
                    sval = None
                    # 方法1: 直接访问属性
                    try:
                        if hasattr(inner_value, 'sVal'):
                            sval = getattr(inner_value, 'sVal', None)
                    except:
                        pass
                    
                    # 方法2: 从字符串表示中提取
                    if sval is None:
                        value_str = str(inner_value)
                        import re
                        match = re.search(r"sVal=b'([^']+)'", value_str)
                        if match:
                            sval = match.group(1).encode('utf-8')
                    
                    # 方法3: 尝试访问内部字典
                    if sval is None:
                        try:
                            if hasattr(inner_value, '__dict__'):
                                d = inner_value.__dict__
                                if 'sVal' in d:
                                    sval = d['sVal']
                        except:
                            pass
                    
                    if sval:
                        print(f"    sVal: {sval}, type: {type(sval)}")
                        if isinstance(sval, bytes):
                            vid_str = sval.decode('utf-8')
                        else:
                            vid_str = str(sval)
                        vid_list.append(vid_str)
                        print(f"    提取VID: {vid_str}")
                    else:
                        print(f"    无法提取sVal，尝试从字符串表示中提取...")
                        # 从ValueWrapper的字符串表示中提取
                        vid_str = str(vid_value).strip('"\'')
                        if vid_str.startswith('entity_'):
                            vid_list.append(vid_str)
                            print(f"    从ValueWrapper字符串提取VID: {vid_str}")
                else:
                    # 尝试直接转换为字符串
                    try:
                        vid_str = str(vid_value).strip('"\'')
                        if vid_str.startswith('entity_'):
                            vid_list.append(vid_str)
                            print(f"    从字符串提取VID: {vid_str}")
                    except:
                        pass
    else:
        print(f"[ERROR] 查询VID失败: {vid_result.error_msg()}")
    
    print(f"\n找到 {len(vid_list)} 个实体VID: {vid_list}")
    
    # 对每个VID使用FETCH PROP查询
    for vid in vid_list:
        print(f"\n--- 查询实体: {vid} ---")
        fetch_query = f'FETCH PROP ON entity "{vid}" YIELD properties(vertex) as props;'
        print(f"执行查询: {fetch_query}")
        
        result = session.execute(fetch_query)
        
        if not result.is_succeeded():
            print(f"[ERROR] 查询失败: {result.error_msg()}")
            continue
        
        print(f"[OK] 查询成功，找到 {result.row_size()} 行数据")
        
        # 解析结果
        for i, row in enumerate(result, 1):
            print(f"\n  行 {i}:")
            row_values = row.values()
            col_names = result.keys()
            
            for j, col_name in enumerate(col_names):
                if j < len(row_values):
                    value = row_values[j]
                    print(f"    字段 {col_name}:")
                    print(f"      value对象: {value}")
                    print(f"      value类型: {type(value)}")
                    
                    # 检查内部结构
                    if hasattr(value, '_value'):
                        inner_value = value._value
                        print(f"      _value类型: {type(inner_value)}")
                        print(f"      _value对象: {inner_value}")
                        
                        # 尝试直接访问sVal属性
                        if hasattr(inner_value, 'sVal'):
                            try:
                                sval = inner_value.sVal
                                if sval is not None:
                                    print(f"      sVal属性: {sval} (type: {type(sval)})")
                                    if isinstance(sval, bytes):
                                        decoded = sval.decode('utf-8')
                                        print(f"      sVal解码后: {decoded}")
                                else:
                                    print(f"      sVal属性: None")
                            except Exception as e:
                                print(f"      sVal访问失败: {e}")
                        
                        # 检查是否是NULL
                        value_str = str(inner_value)
                        if 'nVal=0' in value_str and 'sVal=' not in value_str:
                            print(f"      [判断] 这是NULL值")
                        else:
                            print(f"      [判断] 不是NULL值")
                    else:
                        print(f"      [警告] value对象没有_value属性")
        
        # 同时用MATCH查询查看
        print(f"\n  使用MATCH查询同一实体:")
        match_query = f'MATCH (n:entity) WHERE id(n) == "{vid}" RETURN id(n) as vid, n.name as name, n.type as type, n.mysql_id as mysql_id;'
        match_result = session.execute(match_query)
        
        if match_result.is_succeeded() and match_result.row_size() > 0:
            for row in match_result:
                row_values = row.values()
                col_names = match_result.keys()
                for j, col_name in enumerate(col_names):
                    if j < len(row_values):
                        value = row_values[j]
                        # 尝试提取值
                        extracted = None
                        if hasattr(value, '_value'):
                            inner = value._value
                            if hasattr(inner, 'sVal') and inner.sVal is not None:
                                extracted = inner.sVal.decode('utf-8') if isinstance(inner.sVal, bytes) else inner.sVal
                            elif hasattr(inner, 'iVal') and inner.iVal is not None:
                                extracted = inner.iVal
                        
                        value_str = str(value)
                        if 'nVal=0' in value_str:
                            extracted = "NULL"
                        
                        print(f"      {col_name}: {extracted} (原始: {value_str[:100]})")
    
    session.release()
    pool.close()
    print("\n[SUCCESS] 检查完成")
    
except Exception as e:
    print(f"\n[ERROR] 检查失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

