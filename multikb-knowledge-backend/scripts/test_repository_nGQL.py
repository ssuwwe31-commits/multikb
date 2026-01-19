"""
测试代码仓库节点的 nGQL 语句生成
不连接数据库，只测试语句生成
"""

from datetime import datetime


def escape_string(s: str) -> str:
    """转义字符串中的特殊字符"""
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


def generate_repository_insert(repo_id, repo_name, repo_url, description, 
                                default_branch, last_commit_hash, 
                                total_files, total_lines, knowledge_base_id=0):
    """生成代码仓库节点的 INSERT VERTEX 语句"""
    vid = f"code_repository_{repo_id}"
    
    # 转义字符串
    repo_name_escaped = escape_string(repo_name)
    repo_url_escaped = escape_string(repo_url)
    description_escaped = escape_string(description)
    default_branch_escaped = escape_string(default_branch)
    last_commit_hash_escaped = escape_string(last_commit_hash)
    
    created_at = int(datetime.now().timestamp())
    updated_at = int(datetime.now().timestamp())
    
    # 构建 INSERT VERTEX 语句
    nGQL = (
        f'INSERT VERTEX code_repository('
        f'repo_name, repo_url, description, mysql_id, knowledge_base_id, '
        f'default_branch, last_commit_hash, total_files, total_lines, '
        f'created_at, updated_at'
        f') VALUES "{vid}":('
        f'"{repo_name_escaped}", "{repo_url_escaped}", "{description_escaped}", '
        f'{repo_id}, {knowledge_base_id}, '
        f'"{default_branch_escaped}", "{last_commit_hash_escaped}", '
        f'{total_files}, {total_lines}, '
        f'{created_at}, {updated_at}'
        f');'
    )
    
    return nGQL


if __name__ == "__main__":
    print("=" * 60)
    print("测试代码仓库节点的 nGQL 语句生成")
    print("=" * 60)
    print()
    
    # 测试用例 1: 正常数据
    print("[测试 1] 正常数据")
    nGQL1 = generate_repository_insert(
        repo_id=52,
        repo_name="TabbyML/tabby.git",
        repo_url="https://github.com/TabbyML/tabby.git",
        description="",
        default_branch="main",
        last_commit_hash="b409924ffebd3dbfa50ec9bf91e0ef934eceb067",
        total_files=661,
        total_lines=83754,
        knowledge_base_id=0
    )
    print(nGQL1)
    print()
    
    # 测试用例 2: 包含特殊字符
    print("[测试 2] 包含特殊字符")
    nGQL2 = generate_repository_insert(
        repo_id=53,
        repo_name='Test "Repo"',
        repo_url="https://github.com/test\\repo.git",
        description="Test\ndescription",
        default_branch="main",
        last_commit_hash="abc123",
        total_files=100,
        total_lines=5000
    )
    print(nGQL2)
    print()
    
    # 测试用例 3: 空值处理
    print("[测试 3] 空值处理")
    nGQL3 = generate_repository_insert(
        repo_id=54,
        repo_name="Test/Repo",
        repo_url="https://github.com/test/repo.git",
        description=None,
        default_branch=None,
        last_commit_hash=None,
        total_files=0,
        total_lines=0
    )
    print(nGQL3)
    print()
    
    # 验证语法
    print("[验证] 检查语法问题")
    print("1. 检查括号匹配...")
    open_parens = nGQL1.count('(')
    close_parens = nGQL1.count(')')
    print(f"   左括号: {open_parens}, 右括号: {close_parens}")
    if open_parens == close_parens:
        print("   [OK] 括号匹配")
    else:
        print("   [FAIL] 括号不匹配")
    
    print("2. 检查引号匹配...")
    double_quotes = nGQL1.count('"')
    print(f"   双引号数量: {double_quotes}")
    if double_quotes % 2 == 0:
        print("   [OK] 引号匹配")
    else:
        print("   [FAIL] 引号不匹配")
    
    print("3. 检查字段数量...")
    # 提取字段列表
    fields_part = nGQL1.split('VALUES')[0].split('(')[1].split(')')[0]
    fields = [f.strip() for f in fields_part.split(',')]
    print(f"   字段数量: {len(fields)}")
    print(f"   字段列表: {', '.join(fields)}")
    
    # 提取值列表
    values_part = nGQL1.split('VALUES')[1].split('(')[1].split(')')[0]
    values = [v.strip() for v in values_part.split(',')]
    print(f"   值数量: {len(values)}")
    
    if len(fields) == len(values):
        print("   [OK] 字段和值数量匹配")
    else:
        print(f"   [FAIL] 字段和值数量不匹配: 字段={len(fields)}, 值={len(values)}")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print()
    print("生成的 nGQL 语句可以直接在 NebulaGraph Console 中执行：")
    print("USE multikb_knowledge;")
    print(nGQL1)
