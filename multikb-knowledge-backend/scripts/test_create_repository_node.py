"""
测试创建代码仓库节点的 nGQL 命令
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.graph_storage_service import get_graph_storage
from app.config.settings import settings
from app.core.logging import logger


async def test_create_repository_node():
    """测试创建代码仓库节点"""
    print("=" * 60)
    print("测试创建代码仓库节点")
    print("=" * 60)
    print()
    
    graph = get_graph_storage()
    space = "multikb_knowledge"
    
    # 确保 space 存在
    await graph.create_space_if_not_exists(space)
    
    # 测试数据
    test_repo_id = 999
    vid = f"code_repository_{test_repo_id}"
    
    # 转义字符串中的特殊字符
    def escape_string(s: str) -> str:
        if s is None:
            return ""
        s = str(s)
        # 先转义反斜杠，再转义其他字符
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        # 处理换行符、制表符等，替换为空格
        s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        # 移除可能导致问题的其他控制字符
        s = ''.join(char for char in s if ord(char) >= 32 or char in ['\n', '\r', '\t'])
        return s
    
    # 准备测试数据
    repo_name = "TestRepo/test.git"
    repo_url = "https://github.com/TestRepo/test.git"
    description = "Test repository for testing"
    default_branch = "main"
    last_commit_hash = "abc123def456"
    total_files = 100
    total_lines = 5000
    knowledge_base_id = 0
    created_at = int(datetime.now().timestamp())
    updated_at = int(datetime.now().timestamp())
    
    # 转义字符串
    repo_name_escaped = escape_string(repo_name)
    repo_url_escaped = escape_string(repo_url)
    description_escaped = escape_string(description)
    default_branch_escaped = escape_string(default_branch)
    last_commit_hash_escaped = escape_string(last_commit_hash)
    
    # 构建 INSERT VERTEX 语句
    nGQL = (
        f'INSERT VERTEX code_repository('
        f'repo_name, repo_url, description, mysql_id, knowledge_base_id, '
        f'default_branch, last_commit_hash, total_files, total_lines, '
        f'created_at, updated_at'
        f') VALUES "{vid}":('
        f'"{repo_name_escaped}", "{repo_url_escaped}", "{description_escaped}", '
        f'{test_repo_id}, {knowledge_base_id}, '
        f'"{default_branch_escaped}", "{last_commit_hash_escaped}", '
        f'{total_files}, {total_lines}, '
        f'{created_at}, {updated_at}'
        f');'
    )
    
    print(f"测试 VID: {vid}")
    print(f"Space: {space}")
    print()
    print("生成的 nGQL 语句:")
    print(nGQL)
    print()
    
    # 测试 1: 先确保 schema 存在
    print("[测试 1] 确保 code_repository schema 存在")
    try:
        create_schema = """
        CREATE TAG IF NOT EXISTS code_repository(
            repo_name string,
            repo_url string,
            description string,
            mysql_id int,
            knowledge_base_id int,
            default_branch string,
            last_commit_hash string,
            total_files int,
            total_lines int,
            created_at timestamp,
            updated_at timestamp
        );
        """
        await graph._execute(create_schema, space=space)
        print("✅ Schema 创建/检查成功")
    except Exception as e:
        print(f"❌ Schema 创建失败: {e}")
        return
    print()
    
    # 测试 2: 删除测试节点（如果存在）
    print("[测试 2] 删除测试节点（如果存在）")
    try:
        delete_nGQL = f'DELETE VERTEX "{vid}";'
        await graph._execute(delete_nGQL, space=space)
        print("✅ 测试节点已删除（如果存在）")
    except Exception as e:
        print(f"⚠️ 删除测试节点失败（可能不存在）: {e}")
    print()
    
    # 测试 3: 执行 INSERT 命令
    print("[测试 3] 执行 INSERT VERTEX 命令")
    try:
        result = await graph._execute(nGQL, space=space)
        print("✅ INSERT 命令执行成功")
        print(f"   返回结果: {result}")
    except Exception as e:
        print(f"❌ INSERT 命令执行失败: {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # 测试 4: 验证节点是否创建成功
    print("[测试 4] 验证节点是否创建成功")
    try:
        check_nGQL = f'FETCH PROP ON code_repository "{vid}" YIELD properties(vertex) as props;'
        result = await graph._execute(check_nGQL, space=space)
        if result and len(result) > 0:
            props = result[0].get('props', {})
            print("✅ 节点创建成功，属性如下:")
            print(f"   repo_name: {props.get('repo_name')}")
            print(f"   repo_url: {props.get('repo_url')}")
            print(f"   description: {props.get('description')}")
            print(f"   mysql_id: {props.get('mysql_id')}")
            print(f"   total_files: {props.get('total_files')}")
            print(f"   total_lines: {props.get('total_lines')}")
        else:
            print("❌ 节点未找到")
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 测试 5: 清理测试节点
    print("[测试 5] 清理测试节点")
    try:
        delete_nGQL = f'DELETE VERTEX "{vid}";'
        await graph._execute(delete_nGQL, space=space)
        print("✅ 测试节点已删除")
    except Exception as e:
        print(f"⚠️ 删除测试节点失败: {e}")
    print()
    
    # 测试 6: 测试特殊字符转义
    print("[测试 6] 测试特殊字符转义")
    test_cases = [
        ("正常名称", "TestRepo/test.git"),
        ("包含引号", 'TestRepo "test".git'),
        ("包含反斜杠", "TestRepo\\test.git"),
        ("包含换行符", "TestRepo\ntest.git"),
        ("包含制表符", "TestRepo\ttest.git"),
    ]
    
    for case_name, test_name in test_cases:
        try:
            escaped = escape_string(test_name)
            print(f"   {case_name}: '{test_name}' -> '{escaped}'")
        except Exception as e:
            print(f"   {case_name}: 转义失败 - {e}")
    print()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_create_repository_node())
