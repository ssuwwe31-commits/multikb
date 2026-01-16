# 代码库深度集成 - 快速开始指南

**版本**：v2.0  
**更新日期**：2026-01-12  
**状态**：✅ 已完成

---

## 🚀 快速开始

### 1. 初始化 OpenSearch 索引

在启动服务之前，先初始化代码索引：

```bash
cd multikb-knowledge-backend
python scripts/init_code_indices.py
```

**预期输出**：
```
[SUCCESS] 创建索引成功: code_files
[SUCCESS] 创建索引成功: code_symbols
[OK] 找到 2 个代码相关索引
[SUCCESS] 代码索引初始化完成！
```

---

### 2. 初始化 NebulaGraph 图模式（可选）

如果启用了 NebulaGraph，需要创建代码相关的图模式：

```bash
# 连接到 NebulaGraph
nebula-console -addr 127.0.0.1 -port 9669 -u root -p password

# 切换到你的 Space
USE multikb_knowledge;

# 执行图模式脚本
:source F:/spxknowlage/multikb-knowledge-backend/nebula_schema/code_repository_schema.nGQL
```

**验证**：
```nGQL
SHOW TAGS;      -- 应该看到 code_file, code_symbol, code_repository
SHOW EDGES;     -- 应该看到 imports, calls, inherits, contains 等
SHOW TAG INDEXES;  -- 验证索引创建成功
```

---

### 3. 启动后端服务

```bash
cd multikb-knowledge-backend
python main.py
```

**验证服务**：
访问 `http://localhost:8000/docs` 查看 API 文档，应该能看到：
- ✅ 代码库分析（18个端点）
- ✅ 统一搜索（5个端点）
- ✅ 统一问答（4个端点）

---

### 4. 启动前端服务

```bash
cd multikb-knowledge-frontend
npm run dev
```

访问 `http://localhost:5173`

---

## 🎯 核心功能使用

### 功能 1：关联代码仓库到知识库

#### 方式 1：前端界面

1. 进入知识库详情页
2. 点击 **"💻 代码仓库"** 选项卡
3. 点击 **"关联代码仓库"** 按钮
4. 从下拉列表中选择代码仓库
5. 点击 **"确定"**

#### 方式 2：API 调用

```bash
curl -X POST "http://localhost:8000/api/code-analysis/repositories/1/link-kb?knowledge_base_id=10"
```

**Python 示例**：
```python
import requests

response = requests.post(
    "http://localhost:8000/api/code-analysis/repositories/1/link-kb",
    params={"knowledge_base_id": 10}
)

print(response.json())
```

---

### 功能 2：统一搜索（文档+代码）

#### 前端界面

1. 进入知识库详情页
2. 点击 **"🔍 统一搜索"** 选项卡
3. 输入搜索关键词（如：`依赖注入`）
4. 选择搜索范围：
   - **全部** - 搜索文档和代码
   - **仅文档** - 只搜索文档
   - **仅代码** - 只搜索代码
5. 选择搜索模式：
   - **混合搜索** - 向量+关键词（推荐）
   - **向量搜索** - 语义相似度
   - **关键词** - 精确匹配
6. 点击 **"搜索"**

**搜索结果类型**：
- 📄 **文档** - 显示标题和内容摘要
- 📁 **代码文件** - 显示路径、语言、行数、复杂度
- 🔧 **代码符号** - 显示函数/类名、签名、文档字符串

#### API 调用

```python
import requests

response = requests.post(
    "http://localhost:8000/api/unified-search",
    json={
        "query": "依赖注入",
        "knowledge_base_id": 10,
        "search_scope": ["documents", "code"],
        "search_mode": "hybrid",
        "top_k": 20
    }
)

results = response.json()
print(f"找到 {results['data']['total']} 个结果")

for result in results['data']['results']:
    print(f"- [{result['type']}] {result.get('title') or result.get('file_path')}")
    print(f"  得分: {result['score']:.2f}")
```

---

### 功能 3：智能问答（文档+代码上下文）

#### 前端界面

1. 进入知识库详情页
2. 点击 **"💬 智能问答"** 选项卡
3. 输入问题（如：`FastAPI 如何实现依赖注入？`）
4. 勾选 **"包含代码上下文"**（推荐）
5. 设置 **最大来源数**（默认 5）
6. 点击 **"提问"**

**答案展示**：
- 💬 **智能答案** - 基于文档和代码的综合回答
- 📚 **参考来源** - 显示答案来源（文档/代码文件/代码符号）
- 📊 **相关度** - 每个来源的相关度分数

#### API 调用

```python
response = requests.post(
    "http://localhost:8000/api/unified-qa",
    json={
        "question": "FastAPI 如何实现依赖注入？",
        "knowledge_base_id": 10,
        "search_scope": ["documents", "code"],
        "max_context_items": 5,
        "include_code_context": True
    }
)

answer_data = response.json()['data']
print(f"问题: {answer_data['question']}")
print(f"答案: {answer_data['answer']}")
print(f"来源数: {len(answer_data['sources'])}")
```

---

### 功能 4：获取代码示例

获取某个概念的代码实现示例：

```python
response = requests.post(
    "http://localhost:8000/api/unified-qa/code-examples",
    json={
        "concept": "依赖注入",
        "knowledge_base_id": 10,
        "language": "python",
        "limit": 5
    }
)

examples = response.json()['data']['examples']
for ex in examples:
    print(f"- {ex['symbol_name']} ({ex['symbol_type']})")
    print(f"  文件: {ex['file_path']}")
    print(f"  签名: {ex['signature']}")
    print(f"  代码:\n{ex['code_content']}\n")
```

---

### 功能 5：代码文件和符号管理

#### 获取文件列表

```python
response = requests.get(
    "http://localhost:8000/api/code-analysis/repositories/1/files",
    params={
        "language": "python",
        "page": 1,
        "page_size": 50
    }
)
```

#### 提取文件符号

```python
response = requests.post(
    "http://localhost:8000/api/code-analysis/files/1/extract-symbols"
)
```

#### 同步到图谱

```python
# 同步文件
requests.post("http://localhost:8000/api/code-analysis/files/1/sync-graph")

# 同步符号
requests.post("http://localhost:8000/api/code-analysis/symbols/1/sync-graph")
```

---

## 🔧 配置说明

### 必需配置（.env）

```bash
# 基础配置
MYSQL_HOST=192.168.131.42
MYSQL_DATABASE=spx_knowledge

# Ollama 配置（必需）
OLLAMA_BASE_URL=http://192.168.131.158:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
CODE_LLM_MODEL=qwen2.5-coder:7b

# OpenSearch 配置（必需）
OPENSEARCH_URL=http://localhost:9200

# 代码库配置
CODE_REPO_ENABLED=true
CODE_REPO_CLONE_DIR=/data/code_repositories
```

### 可选配置

```bash
# NebulaGraph 配置（可选，用于图谱功能）
USE_NEBULA_GRAPH=true
NEBULA_HOSTS=127.0.0.1:9669
NEBULA_USER=root
NEBULA_PASSWORD=password
```

---

## 🧪 测试示例

### 端到端测试流程

```python
"""完整的测试流程"""

# 1. 导入代码仓库
response = requests.post(
    "http://localhost:8000/api/code-analysis/repositories",
    params={
        "repo_url": "https://github.com/fastapi/fastapi",
        "branch": "main"
    }
)
repo_id = response.json()['data']['repository_id']
print(f"✅ 创建仓库: {repo_id}")

# 2. 等待克隆和解析完成
# （异步任务，可通过 clone_status 和 parse_status 查询状态）

# 3. 关联到知识库
requests.post(
    f"http://localhost:8000/api/code-analysis/repositories/{repo_id}/link-kb",
    params={"knowledge_base_id": 10}
)
print("✅ 关联到知识库")

# 4. 提取代码文件到数据库
# （这一步在 MVP 版本中通过分析器完成）
# （深度集成版本会自动存储到 code_files 表）

# 5. 向量化代码
# （可通过 Celery 任务异步处理）

# 6. 同步到图谱
# （可通过 API 手动触发，或自动触发）

# 7. 统一搜索测试
response = requests.post(
    "http://localhost:8000/api/unified-search",
    json={
        "query": "依赖注入",
        "knowledge_base_id": 10,
        "search_scope": ["documents", "code"],
        "search_mode": "hybrid",
        "top_k": 10
    }
)
print(f"✅ 搜索结果: {response.json()['data']['total']} 个")

# 8. 统一问答测试
response = requests.post(
    "http://localhost:8000/api/unified-qa",
    json={
        "question": "FastAPI 如何实现依赖注入？",
        "knowledge_base_id": 10,
        "search_scope": ["documents", "code"],
        "max_context_items": 5
    }
)
answer = response.json()['data']
print(f"✅ 问答答案: {answer['answer'][:100]}...")
print(f"✅ 来源数量: {len(answer['sources'])}")
```

---

## 📊 功能对比

| 功能 | MVP 版本 | 深度集成版本 |
|------|---------|-------------|
| 代码仓库管理 | ✅ | ✅ |
| 代码解析 | ✅ | ✅ |
| 代码问答 | ✅ | ✅ |
| **知识库关联** | ❌ | ✅ ⭐ |
| **代码文件数据库存储** | ❌ | ✅ ⭐ |
| **代码符号数据库存储** | ❌ | ✅ ⭐ |
| **图谱集成** | ❌ | ✅ ⭐ |
| **代码向量化** | ❌ | ✅ ⭐ |
| **统一搜索** | ❌ | ✅ ⭐ |
| **统一问答** | ❌ | ✅ ⭐ |
| **代码-文档映射** | ❌ | ✅ ⭐ |

---

## 🌟 核心优势

### 1. 统一知识管理

**传统方式**：
- 文档存在知识库
- 代码存在 Git 仓库
- 两者分离，查询困难

**深度集成后**：
- ✅ 文档 + 代码 = 统一知识库
- ✅ 一次搜索，全面结果
- ✅ 文档引用代码，代码关联文档

### 2. 智能检索能力

**传统搜索**：
- 只能搜索文档内容
- 关键词精确匹配
- 无法搜索代码

**统一搜索**：
- ✅ 文档 + 代码混合搜索
- ✅ 向量搜索（语义理解）
- ✅ 代码文件、符号、注释全覆盖
- ✅ 智能排序和融合

### 3. 知识图谱洞察

**传统方式**：
- 文档之间无关联
- 代码依赖难以可视化

**图谱集成后**：
- ✅ 文档-实体-代码的关联
- ✅ 代码调用链可视化
- ✅ 依赖关系分析
- ✅ 概念实现追踪

### 4. 智能问答增强

**传统问答**：
- 仅基于文档内容
- 无法引用代码示例

**统一问答**：
- ✅ 文档 + 代码双重上下文
- ✅ 自动引用代码片段
- ✅ 代码实现说明
- ✅ 多源答案融合

---

## 🎬 使用场景

### 场景 1：项目文档 + 代码

**需求**：管理项目的设计文档和实现代码

**步骤**：
1. 创建知识库"FastAPI 项目"
2. 上传设计文档、API 文档
3. 关联代码仓库 `fastapi/fastapi`
4. 使用统一搜索查询"依赖注入"
5. 结果：设计文档 + API 文档 + 代码实现

**价值**：
- 📚 文档和代码统一管理
- 🔍 一次搜索获得完整信息
- 💡 新人快速理解项目

---

### 场景 2：技术学习

**需求**：学习某个技术栈（如 FastAPI）

**步骤**：
1. 创建知识库"FastAPI 学习"
2. 上传 FastAPI 教程文档
3. 关联 FastAPI 源码仓库
4. 提问："FastAPI 的路由是如何实现的？"
5. 答案：教程说明 + 源码实现 + 代码示例

**价值**：
- 📖 理论 + 实践结合
- 🎯 精准学习路径
- 💻 代码示例即时获取

---

### 场景 3：代码审查

**需求**：审查代码质量和设计

**步骤**：
1. 导入项目代码仓库
2. 上传设计文档、编码规范
3. 搜索特定模式（如"单例模式"）
4. 结果：规范文档 + 实际实现
5. 对比分析是否符合规范

**价值**：
- 🔍 快速定位代码模式
- 📋 对照规范检查
- 🎯 发现不符合规范的代码

---

### 场景 4：API 文档 + 实现

**需求**：维护 API 文档和代码一致性

**步骤**：
1. 创建知识库"API 文档"
2. 上传 API 文档
3. 关联后端代码仓库
4. 搜索某个 API 端点
5. 结果：API 文档 + 实现代码

**价值**：
- 📖 文档和代码同步查看
- 🔗 API 定义与实现关联
- ✅ 发现文档与代码不一致

---

## 🛠️ 高级功能

### 1. 批量操作

#### 批量向量化仓库

```python
from app.services.code_vectorization_service import get_code_vectorization_service

# 向量化整个仓库
service = get_code_vectorization_service(db)
stats = await service.batch_vectorize_repository(
    repository_id=1,
    include_symbols=True
)

print(f"文件: {stats['files']['success']}/{stats['files']['total']}")
print(f"符号: {stats['symbols']['success']}/{stats['symbols']['total']}")
```

#### 批量同步到图谱

```python
from app.services.code_file_service import get_code_file_service

service = get_code_file_service(db)
stats = await service.batch_sync_to_graph(repository_id=1)

print(f"同步完成: {stats['success']}/{stats['total']}")
```

### 2. 图谱查询

#### 查询代码调用链

```nGQL
# 查询从 main 函数开始的调用链（最多3层）
MATCH path = (s1:code_symbol {symbol_name: "main"})
             -[:calls*1..3]->
             (s2:code_symbol)
RETURN path
LIMIT 50;
```

#### 查询文档引用的代码

```nGQL
# 查询某个知识库中文档引用的代码
MATCH (d:document)-[r:references]->(c:code_file)
WHERE d.knowledge_base_id == 10
RETURN d.title, c.file_path, r.reference_type, r.confidence
ORDER BY r.confidence DESC
LIMIT 20;
```

#### 查询概念的代码实现

```nGQL
# 查询"依赖注入"概念的代码实现
MATCH (entity:entity {name: "依赖注入"})
      -[:implements]->
      (symbol:code_symbol)
RETURN entity.name, symbol.qualified_name, symbol.signature
LIMIT 10;
```

### 3. 向量搜索

#### 使用向量直接搜索

```python
from app.services.vector_service import VectorService
from app.services.unified_search_service import get_unified_search_service

# 1. 生成查询向量
vector_service = VectorService()
query_vector = await vector_service.generate_embedding("依赖注入")

# 2. 向量搜索
search_service = get_unified_search_service(db)
results = await search_service.search_by_vector(
    vector=query_vector,
    search_scope=["documents", "code"],
    knowledge_base_id=10,
    top_k=20
)

print(f"找到 {results['total']} 个结果")
```

---

## 🐛 故障排查

### 问题 1：OpenSearch 索引未创建

**症状**：搜索时报错 `index_not_found_exception`

**解决**：
```bash
python scripts/init_code_indices.py
```

---

### 问题 2：NebulaGraph 图模式未初始化

**症状**：同步到图谱时报错

**解决**：
```bash
nebula-console -addr 127.0.0.1 -port 9669 -u root -p password
USE multikb_knowledge;
:source nebula_schema/code_repository_schema.nGQL
```

---

### 问题 3：代码仓库未关联知识库

**症状**：统一搜索无法搜到代码

**解决**：
1. 确认代码仓库已克隆完成（`clone_status = completed`）
2. 关联代码仓库到知识库
3. 等待向量化完成

---

### 问题 4：向量化未完成

**症状**：搜索代码时无结果

**解决**：
```python
# 手动触发向量化
from app.services.code_vectorization_service import get_code_vectorization_service

service = get_code_vectorization_service(db)
await service.batch_vectorize_repository(repository_id=1)
```

---

## 📚 相关文档

| 文档 | 路径 | 用途 |
|------|------|------|
| 完成报告 | `CODE-INTEGRATION-COMPLETE.md` | 查看完整实施清单 |
| 进度报告 | `CODE-INTEGRATION-PROGRESS.md` | 查看实施进度 |
| 设计文档 | `docs/architecture/code-repository-integration-design.md` | 查看设计细节 |
| 迁移指南 | `MIGRATION-GUIDE.md` | 数据库迁移说明 |
| MVP 快速开始 | `CODE-REPOSITORY-QUICKSTART.md` | MVP 功能使用 |

---

## 🎉 总结

代码库深度集成功能已全部完成，现在你可以：

1. ✅ **关联代码仓库到知识库** - 文档+代码统一管理
2. ✅ **统一搜索** - 一次搜索，文档和代码全覆盖
3. ✅ **智能问答** - 跨文档+代码的智能回答
4. ✅ **图谱可视化** - 代码依赖和调用关系
5. ✅ **代码示例获取** - 按概念查找代码实现

**开始使用吧！** 🚀

---

**文档版本**：v2.0  
**最后更新**：2026-01-12  
**编写者**：AI Assistant
