"""
检查 NebulaGraph 中的代码仓库数据
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


async def check_repository_data(repo_id: int):
    """检查指定仓库的数据"""
    print("=" * 60)
    print(f"检查仓库 {repo_id} 的数据")
    print("=" * 60)
    print()
    
    graph = get_graph_storage()
    space = "multikb_knowledge"
    repo_vid = f"code_repository_{repo_id}"
    
    # 确保 space 存在
    await graph.create_space_if_not_exists(space)
    
    # 1. 检查仓库节点是否存在
    print(f"[检查 1] 检查仓库节点: {repo_vid}")
    try:
        check_repo_nGQL = f'FETCH PROP ON code_repository "{repo_vid}" YIELD properties(vertex) as props;'
        result = await graph._execute(check_repo_nGQL, space=space)
        if result and len(result) > 0:
            props = result[0].get('props', {})
            print(f"✅ 仓库节点存在")
            print(f"   repo_name: {props.get('repo_name')}")
            print(f"   repo_url: {props.get('repo_url')}")
            print(f"   total_files: {props.get('total_files')}")
            print(f"   total_lines: {props.get('total_lines')}")
        else:
            print(f"❌ 仓库节点不存在")
            return
    except Exception as e:
        print(f"❌ 检查仓库节点失败: {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # 2. 检查文件节点数量
    print(f"[检查 2] 检查文件节点数量")
    try:
        count_files_nGQL = f"""
        MATCH (repo:code_repository)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(file) as file_count;
        """
        result = await graph._execute(count_files_nGQL, space=space)
        if result and len(result) > 0:
            file_count = result[0].get('file_count', 0)
            print(f"✅ 找到 {file_count} 个文件节点")
        else:
            print(f"❌ 查询失败或返回空结果")
    except Exception as e:
        print(f"❌ 检查文件节点数量失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 3. 检查 contains 边数量
    print(f"[检查 3] 检查 contains 边数量")
    try:
        count_edges_nGQL = f"""
        MATCH (repo:code_repository)-[e:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN count(e) as edge_count;
        """
        result = await graph._execute(count_edges_nGQL, space=space)
        if result and len(result) > 0:
            edge_count = result[0].get('edge_count', 0)
            print(f"✅ 找到 {edge_count} 条 contains 边")
        else:
            print(f"❌ 查询失败或返回空结果")
    except Exception as e:
        print(f"❌ 检查 contains 边失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 4. 列出前10个文件节点
    print(f"[检查 4] 列出前10个文件节点")
    try:
        list_files_nGQL = f"""
        MATCH (repo:code_repository)-[:contains]->(file:code_file)
        WHERE id(repo) == "{repo_vid}"
        RETURN id(file) as vid, file.file_path as file_path, file.language as language
        LIMIT 10;
        """
        result = await graph._execute(list_files_nGQL, space=space)
        if result and len(result) > 0:
            print(f"✅ 找到 {len(result)} 个文件节点（前10个）:")
            for idx, row in enumerate(result, 1):
                print(f"   [{idx}] VID: {row.get('vid')}")
                print(f"       路径: {row.get('file_path')}")
                print(f"       语言: {row.get('language')}")
        else:
            print(f"❌ 没有找到文件节点")
    except Exception as e:
        print(f"❌ 列出文件节点失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 5. 检查所有 code_file 节点（不通过 contains 边）
    print(f"[检查 5] 检查所有 code_file 节点（不通过边）")
    try:
        count_all_files_nGQL = """
        MATCH (file:code_file)
        RETURN count(file) as total_files;
        """
        result = await graph._execute(count_all_files_nGQL, space=space)
        if result and len(result) > 0:
            total_files = result[0].get('total_files', 0)
            print(f"✅ 图数据库中总共有 {total_files} 个 code_file 节点")
        else:
            print(f"❌ 查询失败")
    except Exception as e:
        print(f"❌ 检查所有文件节点失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 6. 检查所有 code_repository 节点
    print(f"[检查 6] 检查所有 code_repository 节点")
    try:
        list_repos_nGQL = """
        MATCH (repo:code_repository)
        RETURN id(repo) as vid, repo.repo_name as repo_name
        LIMIT 20;
        """
        result = await graph._execute(list_repos_nGQL, space=space)
        if result and len(result) > 0:
            print(f"✅ 找到 {len(result)} 个仓库节点:")
            for idx, row in enumerate(result, 1):
                print(f"   [{idx}] VID: {row.get('vid')}, 名称: {row.get('repo_name')}")
        else:
            print(f"❌ 没有找到仓库节点")
    except Exception as e:
        print(f"❌ 检查仓库节点失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 7. 检查是否有孤立文件节点（没有 contains 边）
    print(f"[检查 7] 检查孤立文件节点（没有 contains 边）")
    try:
        orphan_files_nGQL = """
        MATCH (file:code_file)
        WHERE NOT (file)<-[:contains]-()
        RETURN count(file) as orphan_count
        LIMIT 1;
        """
        result = await graph._execute(orphan_files_nGQL, space=space)
        if result and len(result) > 0:
            orphan_count = result[0].get('orphan_count', 0)
            if orphan_count > 0:
                print(f"⚠️ 发现 {orphan_count} 个孤立文件节点（没有 contains 边）")
            else:
                print(f"✅ 没有孤立文件节点")
        else:
            print(f"❌ 查询失败")
    except Exception as e:
        print(f"❌ 检查孤立文件节点失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    print("=" * 60)
    print("检查完成")
    print("=" * 60)


async def main():
    """主函数"""
    import sys
    
    # 从命令行参数获取 repo_id，如果没有则检查所有仓库
    if len(sys.argv) > 1:
        try:
            repo_id = int(sys.argv[1])
            await check_repository_data(repo_id)
        except ValueError:
            print(f"错误: 无效的仓库ID: {sys.argv[1]}")
            print("用法: python check_nebula_data.py [repo_id]")
    else:
        # 检查所有仓库
        print("未指定仓库ID，检查所有仓库...")
        print()
        
        graph = get_graph_storage()
        space = "multikb_knowledge"
        await graph.create_space_if_not_exists(space)
        
        # 列出所有仓库
        list_repos_nGQL = """
        MATCH (repo:code_repository)
        RETURN id(repo) as vid, repo.repo_name as repo_name, repo.mysql_id as mysql_id
        LIMIT 50;
        """
        try:
            result = await graph._execute(list_repos_nGQL, space=space)
            if result and len(result) > 0:
                print(f"找到 {len(result)} 个仓库:")
                for row in result:
                    vid = row.get('vid')
                    repo_name = row.get('repo_name')
                    mysql_id = row.get('mysql_id')
                    print(f"  - VID: {vid}, MySQL ID: {mysql_id}, 名称: {repo_name}")
                    
                    # 检查每个仓库的文件数量
                    count_nGQL = f"""
                    MATCH (repo:code_repository)-[:contains]->(file:code_file)
                    WHERE id(repo) == "{vid}"
                    RETURN count(file) as file_count;
                    """
                    try:
                        count_result = await graph._execute(count_nGQL, space=space)
                        if count_result and len(count_result) > 0:
                            file_count = count_result[0].get('file_count', 0)
                            print(f"    文件数: {file_count}")
                        else:
                            print(f"    文件数: 0 (查询失败)")
                    except Exception as e:
                        print(f"    文件数: 查询失败 - {e}")
                    print()
            else:
                print("❌ 没有找到任何仓库节点")
        except Exception as e:
            print(f"❌ 查询仓库列表失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
