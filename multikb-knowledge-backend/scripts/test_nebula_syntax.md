# NebulaGraph 查询语法测试说明

## 已修复的查询语法

我已经修复了所有 NebulaGraph 查询，使用以下语法：

### 修复前（错误的语法）：
```nGQL
MATCH (repo)
WHERE id(repo) == "code_repository_50"
WITH repo
MATCH (repo)-[:contains]->(file:code_file)
RETURN id(file) as vid
LIMIT 10000 OFFSET 0;  -- ❌ OFFSET 不支持
```

### 修复后（正确的语法）：
```nGQL
MATCH (repo)-[:contains]->(file:code_file)
WHERE id(repo) == "code_repository_50"
RETURN id(file) as vid
SKIP 0 LIMIT 10000;  -- ✅ 使用 SKIP 代替 OFFSET
```

## 关键修复点

1. **使用单个 MATCH 语句**：更简单、更可靠
2. **使用 SKIP 代替 OFFSET**：NebulaGraph 的 OpenCypher 兼容语法使用 `SKIP`
3. **移除 WITH 子句**：不再需要多个 MATCH 语句

## 如何测试

### 方法 1：通过后端服务测试

1. 确保后端服务正在运行
2. 访问依赖关系页面
3. 查看日志，应该不再有语法错误

### 方法 2：直接使用 NebulaGraph Console 测试

```bash
# 连接到 NebulaGraph
nebula-console -addr 127.0.0.1 -port 9669 -u root -p password

# 切换到 Space
USE multikb_knowledge;

# 测试查询（替换 repo_vid）
MATCH (repo)-[:contains]->(file:code_file)
WHERE id(repo) == "code_repository_50"
RETURN id(file) as vid
LIMIT 10;
```

### 方法 3：运行测试脚本

```bash
cd multikb-knowledge-backend
python scripts/test_nebula_queries.py
```

**注意**：需要确保：
- NebulaGraph 服务正在运行
- 已安装 `nebula3-python`：`pip install nebula3-python`
- 环境变量配置正确（NEBULA_HOSTS, NEBULA_USER, NEBULA_PASSWORD）

## 修复的查询位置

1. `app/services/nebula_code_service.py`:
   - `get_dependency_graph()` 方法
   - `get_repository_files()` 方法（文件列表查询）
   - `get_repository_files()` 方法（计数查询）

## 预期结果

修复后，查询应该：
- ✅ 不再出现 `syntax error near ')'` 错误
- ✅ 能够正确查询文件列表
- ✅ 能够正确查询依赖关系

如果仍有问题，可能是：
1. NebulaGraph 中没有数据（需要先运行代码分析任务）
2. NebulaGraph 版本兼容性问题
3. 需要重启后端服务使代码生效
