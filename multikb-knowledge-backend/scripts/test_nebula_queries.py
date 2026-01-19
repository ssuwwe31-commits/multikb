"""
测试 NebulaGraph 查询语法
用于诊断代码仓库查询问题
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.graph_storage_service import get_graph_storage
from app.config.settings import settings
from app.core.logging import logger


async def test_queries():
    """测试各种查询语法"""
    print("=" * 60)
    print("测试 NebulaGraph 查询语法")
    print("=" * 60)
    print()
    
    graph = get_graph_storage()
    space = "multikb_knowledge"
    repo_vid = "code_repository_50"
    
    # 确保 space 存在
    await graph.create_space_if_not_exists(space)
    
    print(f"测试仓库 VID: {repo_vid}")
    print(f"Space: {space}")
    print()
    
    # 测试 1: 检查仓库节点是否存在（使用单引号）
    print("[测试 1] 检查仓库节点是否存在（使用单引号）")
    try:
        check_repo_nGQL = f"""
        MATCH (repo)
        WHERE id(repo) == '{repo_vid}'
        RETURN id(repo) as vid, labels(repo) as tags;
        """
        result = await graph._execute(check_repo_nGQL, space=space)
        if result:
            print(f"[OK] 仓库节点存在: {result}")
        else:
            print(f"[FAIL] 仓库节点不存在")
    except Exception as e:
        print(f"[FAIL] 查询失败: {e}")
    print()
    
    # 测试 1b: 检查仓库节点是否存在（使用双引号）
    print("[测试 1b] 检查仓库节点是否存在（使用双引号）")
    try:
        check_repo_nGQL = f"""
        MATCH (repo)
        WHERE id(repo) == "{repo_vid}"
        RETURN id(repo) as vid, labels(repo) as tags;
        """
        result = await graph._execute(check_repo_nGQL, space=space)
        if result:
            print(f"[OK] 仓库节点存在: {result}")
        else:
            print(f"[FAIL] 仓库节点不存在")
    except Exception as e:
        print(f"[FAIL] 查询失败: {e}")
    print()
    
    # 测试 2: 使用单个 MATCH 查询（使用单引号）
    print("[测试 2] 使用单个 MATCH 查询（使用单引号）")
    try:
        query1 = f"""
        MATCH (repo)-[:contains]->(file:code_file)
        WHERE id(repo) == '{repo_vid}'
        RETURN id(file) as vid
        LIMIT 10;
        """
        result = await graph._execute(query1, space=space)
        print(f"[OK] 查询成功: 找到 {len(result)} 个文件")
        if result:
            print(f"   示例 VID: {result[0]}")
    except Exception as e:
        print(f"[FAIL] 查询失败: {e}")
    print()
    
    # 测试 3: 使用 SKIP 和 LIMIT（分页）
    print("[测试 3] 使用 SKIP 和 LIMIT（分页）")
    try:
        query2 = f"""
        MATCH (repo)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN id(file) as vid
        SKIP 0 LIMIT 10;
        """
        result = await graph._execute(query2, space=space)
        print(f"✅ 查询成功: 找到 {len(result)} 个文件")
        if result:
            print(f"   示例 VID: {result[0]}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()
    
    # 测试 4: 计数查询
    print("[测试 4] 计数查询")
    try:
        query3 = f"""
        MATCH (repo)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(file) as total;
        """
        result = await graph._execute(query3, space=space)
        print(f"✅ 查询成功: {result}")
        if result:
            print(f"   文件总数: {result[0].get('total', 0)}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()
    
    # 测试 5: 带语言过滤的查询
    print("[测试 5] 带语言过滤的查询")
    try:
        query4 = f"""
        MATCH (repo)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}" AND file.language == "python"
        RETURN id(file) as vid
        LIMIT 10;
        """
        result = await graph._execute(query4, space=space)
        print(f"✅ 查询成功: 找到 {len(result)} 个 Python 文件")
        if result:
            print(f"   示例 VID: {result[0]}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()
    
    # 测试 6: 检查 contains 边是否存在
    print("[测试 6] 检查 contains 边是否存在")
    try:
        query5 = f"""
        MATCH (repo)-[e:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(e) as edge_count
        LIMIT 1;
        """
        result = await graph._execute(query5, space=space)
        print(f"✅ 查询成功: {result}")
        if result:
            print(f"   Contains 边数量: {result[0].get('edge_count', 0)}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()
    
    # 测试 7: 列出所有 code_repository 节点
    print("[测试 7] 列出所有 code_repository 节点")
    try:
        query6 = """
        MATCH (repo)
        WHERE "code_repository" IN labels(repo)
        RETURN id(repo) as vid
        LIMIT 10;
        """
        result = await graph._execute(query6, space=space)
        print(f"✅ 查询成功: 找到 {len(result)} 个仓库节点")
        if result:
            for row in result[:5]:
                print(f"   VID: {row.get('vid')}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()
    
    # 测试 8: 列出所有 code_file 节点
    print("[测试 8] 列出所有 code_file 节点")
    try:
        query7 = """
        MATCH (file:code_file)
        RETURN id(file) as vid
        LIMIT 10;
        """
        result = await graph._execute(query7, space=space)
        print(f"✅ 查询成功: 找到 {len(result)} 个文件节点")
        if result:
            for row in result[:5]:
                print(f"   VID: {row.get('vid')}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()
    
    # 测试 9: 检查特定仓库的所有边
    print("[测试 9] 检查特定仓库的所有边")
    try:
        query8 = f"""
        MATCH (repo)-[e]->(target)
        WHERE id(repo) == "{repo_vid}"
        RETURN type(e) as edge_type, count(*) as count
        LIMIT 20;
        """
        result = await graph._execute(query8, space=space)
        print(f"✅ 查询成功: 找到 {len(result)} 种边类型")
        if result:
            for row in result:
                print(f"   边类型: {row.get('edge_type')}, 数量: {row.get('count')}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_queries())
