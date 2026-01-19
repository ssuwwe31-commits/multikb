# 🎓 MultiKB Knowledge Base - 智能知识管理系统

一个基于 AI 的智能知识库管理系统，支持文档管理、代码分析、知识图谱、智能搜索和问答。

**版本**: v2.0  
**最新更新**: 2026-01-12 - 代码库深度集成完成 ✅

---

## ✨ 核心特性

### 📚 文档管理
- ✅ 多格式文档上传（PDF, Word, Excel, Markdown等）
- ✅ 文档分块和向量化
- ✅ 文档版本管理
- ✅ 文档推荐和自动标签

### 💻 代码分析（⭐ v2.0 新增）
- ✅ GitHub/GitLab 代码仓库导入
- ✅ 多语言代码解析（Python, JavaScript, Java等）
- ✅ 代码符号提取（函数、类、方法）
- ✅ 依赖关系分析
- ✅ 代码质量分析

### 🔍 统一搜索（⭐ v2.0 新增）
- ✅ 文档+代码混合搜索
- ✅ 向量搜索（语义理解）
- ✅ 关键词搜索（精确匹配）
- ✅ 混合搜索（智能排序）

### 💬 智能问答（⭐ v2.0 新增）
- ✅ 跨文档+代码的上下文问答
- ✅ 代码片段引用
- ✅ 多源信息融合
- ✅ 来源追溯

### 🕸️ 知识图谱
- ✅ 实体关系管理
- ✅ 文档-实体-代码关联（⭐ v2.0）
- ✅ 图谱可视化
- ✅ 路径查询和分析

### 🤖 AI 能力
- ✅ Ollama 本地 LLM 集成
- ✅ 代码专用模型（qwen2.5-coder:7b）
- ✅ 向量化模型（nomic-embed-text）
- ✅ 智能推荐和自动标签

---

## 🏗️ 技术架构

### 后端技术栈
- **框架**: FastAPI + Python 3.9+
- **数据库**: MySQL 8.0+
- **向量检索**: OpenSearch 2.x
- **知识图谱**: NebulaGraph 3.8+（可选）
- **缓存**: Redis 6.x
- **对象存储**: MinIO
- **AI 模型**: Ollama
- **任务队列**: Celery

### 前端技术栈
- **框架**: Vue 3 + TypeScript
- **UI 组件**: Element Plus
- **构建工具**: Vite
- **图表**: ECharts
- **状态管理**: Pinia

---

## 🚀 快速开始

### 1. 环境要求

- **Python**: 3.9+
- **Node.js**: 16+
- **MySQL**: 8.0+
- **Redis**: 6.x
- **OpenSearch**: 2.x
- **Ollama**: 最新版（含 nomic-embed-text 和 qwen2.5-coder:7b 模型）

### 2. 后端启动

```bash
# 克隆项目
git clone <repository-url>
cd spxknowlage/multikb-knowledge-backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库、OpenSearch、Ollama 等

# 初始化数据库
mysql -u root -p < init.sql

# 执行迁移（代码库集成）
mysql -u root -p spx_knowledge < migrations/2026011201_code_repository_mvp.sql
mysql -u root -p spx_knowledge < migrations/2026011202_code_integration.sql

# 初始化 OpenSearch 代码索引
python scripts/init_code_indices.py

# 启动服务
python main.py
```

### 3. 前端启动

```bash
cd spxknowlage/multikb-knowledge-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问系统

- **前端**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

---

## 📖 文档导航

详细文档请查看 [docs](./docs) 目录：

### 快速开始
- [代码库集成快速开始](docs/guides/CODE-INTEGRATION-QUICKSTART.md) - 详细使用指南
- [项目总结](docs/guides/README-CODE-INTEGRATION.md) - 代码库集成总结

### 架构设计
- [数据存储架构](docs/architecture/DATA_STORAGE_ARCHITECTURE.md) - 数据存储架构说明
- [代码库集成设计](docs/architecture/code-repository-integration-design.md) - 完整技术设计
- [代码问答逻辑分析](docs/architecture/CODE_QA_LOGIC_ANALYSIS.md) - 代码问答系统完整逻辑
- [React Agent 设计](docs/architecture/CODE_ANALYSIS_REACT_AGENT_DESIGN.md) - React Agent 架构设计

### 开发文档
- [代码库处理流程](docs/development/CODE_REPOSITORY_PROCESS_FLOW.md) - 从克隆到 Wiki 的完整流程
- [LLM 使用与优化总结](docs/development/LLM_AND_OPTIMIZATION_SUMMARY.md) - LLM 使用情况与优化建议
- [代码分析与 Function Calling](docs/development/CODE_ANALYSIS_AND_FUNCTION_CALLING.md) - Function Calling 实现与优化
- [性能优化计划](docs/development/PERFORMANCE_OPTIMIZATION_PLAN.md) - 性能优化实施计划
- [代码检查总结](docs/development/CODE_REVIEW_SUMMARY.md) - 代码检查报告

### 参考文档
- [返回类型字段说明](docs/reference/RETURN_TYPE_FIELD_EXPLANATION.md) - return_type 字段详细说明

### 部署和运维
- [数据库迁移指南](multikb-knowledge-backend/MIGRATION-GUIDE.md) - 数据库迁移
- [快速部署](multikb-knowledge-frontend/QUICK_DEPLOY.md) - 生产环境部署

---

## 🎯 核心功能使用

### 1. 创建知识库

1. 登录系统
2. 点击 **"创建知识库"**
3. 填写知识库信息
4. 选择分类和标签

### 2. 上传文档

1. 进入知识库详情页
2. 点击 **"上传文档"**
3. 选择文件（支持 PDF, Word, Excel, Markdown 等）
4. 等待处理完成

### 3. 导入代码仓库（⭐ v2.0）

1. 进入 **"代码库分析"** 页面
2. 点击 **"导入仓库"**
3. 输入 Git 仓库地址
4. 选择分支（默认 main）
5. 等待克隆和解析

### 4. 关联代码到知识库（⭐ v2.0）

1. 进入知识库详情页
2. 点击 **"代码仓库"** 选项卡
3. 点击 **"关联代码仓库"**
4. 选择已导入的代码仓库
5. 确认关联

### 5. 统一搜索（⭐ v2.0）

1. 进入知识库详情页
2. 点击 **"统一搜索"** 选项卡
3. 输入搜索关键词
4. 选择搜索范围（全部/文档/代码）
5. 选择搜索模式（混合/向量/关键词）
6. 查看搜索结果（文档、代码文件、代码符号混合显示）

### 6. 智能问答（⭐ v2.0）

1. 进入知识库详情页
2. 点击 **"智能问答"** 选项卡
3. 输入问题
4. 勾选 **"包含代码上下文"**（推荐）
5. 点击 **"提问"**
6. 查看答案和来源

---

## 🎨 主要页面

### 知识库列表
- 查看所有知识库
- 搜索和筛选
- 创建新知识库

### 知识库详情（扩展版 ⭐ v2.0）
- 📄 **文档列表** - 查看和管理文档
- 💻 **代码仓库** - 关联和管理代码仓库
- 🔍 **统一搜索** - 搜索文档和代码
- 💬 **智能问答** - 跨文档+代码问答

### 代码库分析（⭐ v2.0 新增）
- 导入代码仓库
- 查看代码结构
- 代码质量分析
- 依赖关系图
- 代码问答

### 知识图谱
- 实体管理
- 关系管理
- 图谱可视化
- 路径查询

---

## 🔧 配置说明

### 必需配置

```bash
# .env 文件

# MySQL
MYSQL_HOST=192.168.131.42
MYSQL_DATABASE=spx_knowledge
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password

# OpenSearch
OPENSEARCH_URL=http://localhost:9200

# Ollama
OLLAMA_BASE_URL=http://192.168.131.158:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
CODE_LLM_MODEL=qwen2.5-coder:7b

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### 可选配置

```bash
# NebulaGraph（用于知识图谱）
USE_NEBULA_GRAPH=true
NEBULA_HOSTS=127.0.0.1:9669
NEBULA_USER=root
NEBULA_PASSWORD=password
NEBULA_SPACE=multikb_knowledge
```

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│  Vue 3 + TypeScript + Element Plus                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        API 层                                │
│  FastAPI REST API (27 个代码相关端点)                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       服务层                                 │
│  6 个核心代码服务 + 其他业务服务                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     数据存储层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   MySQL      │  │ NebulaGraph  │  │ OpenSearch   │    │
│  │  关系存储    │  │  图谱存储    │  │  向量检索    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎊 v2.0 更新内容

### 代码库深度集成（2026-01-12）

#### 数据库层
- ✅ 6 张新表（code_repositories, code_files, code_symbols 等）
- ✅ 9 个外键约束
- ✅ 20+ 优化索引

#### 知识图谱层
- ✅ 3 个新顶点类型（code_repository, code_file, code_symbol）
- ✅ 7 个新边类型（imports, calls, inherits 等）
- ✅ 11 个图谱索引

#### 向量检索层
- ✅ 2 个 OpenSearch 索引（code_files, code_symbols）
- ✅ 1024 维向量字段
- ✅ HNSW 算法优化

#### 服务层
- ✅ 6 个新服务（NebulaCodeService, CodeFileService 等）
- ✅ 代码向量化服务
- ✅ 统一搜索服务
- ✅ 统一问答服务

#### API 层
- ✅ 27 个新端点
- ✅ 代码库管理 (12 个)
- ✅ 统一搜索 (5 个)
- ✅ 统一问答 (4 个)

#### 前端层
- ✅ 2 个新组件（UnifiedSearch, UnifiedQA）
- ✅ 知识库详情页扩展（4 个选项卡）
- ✅ 3 个 API 模块

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

---

## 📝 许可证

[MIT License](LICENSE)

---

## 📧 联系方式

如有问题或建议，请提交 Issue 或联系开发团队。

---

**项目状态**: ✅ 生产就绪  
**最新版本**: v2.0  
**最后更新**: 2026-01-12

**开始使用 MultiKB，让知识管理更智能！** 🚀
