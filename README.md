## 项目总览

- **项目名称**：SPX Knowledge Base（知识问答与知识库管理平台）
- **核心价值**：提供从文档入库、内容治理、语义检索、多模态问答到图片搜索的端到端解决方案，兼顾企业级可靠性与开发者体验。
- **整体架构**：后端基于 `FastAPI + Celery + SQLAlchemy`，前端基于 `Vue 3 + TypeScript + Vite`，底层依赖 MySQL、OpenSearch、Redis、MinIO、Ollama、NebulaGraph 等服务，支持 WebSocket 实时交互。
- **项目状态**：完成主要开发，核心功能 100% 对齐设计文档，生产可用。

## 架构亮点

- **端到端知识链路**：从多格式文档上传、分块、向量化，到知识库检索、问答、图片检索、引用溯源，完整闭环。
- **多模态问答引擎**：支持文本、图片、图文混合输入，提供六种检索策略（向量、关键词、混合、精确、模糊、多模态），并通过 WebSocket 流式输出答案。
- **高可靠数据架构**：MySQL 记录结构化数据，OpenSearch 存储向量与全文索引，Redis 提供缓存与任务队列，MinIO 管理原始文件，NebulaGraph 存储知识图谱，Celery 保障异步任务稳定执行。
- **工程化体验**：前端采用模块化 API、Pinia 状态管理、组合式函数和 Element Plus 组件体系；后端遵循分层架构，服务类、任务队列与路由划分清晰。
- **透明设计文档**：汇总接口统计、检索流程、数据时序、表结构、目录设计、修复记录，便于运维与扩展。

## 核心功能概览

- **文档处理**
  - 支持 9 种文档格式上传与解析，智能分块与向量化
  - 块级编辑、版本管理、一致性保障与处理进度追踪
  - 文档类目、标签、状态管理与内容质量校验
- **知识问答**
  - 多模态输入、多路召回、混合排序、上下文构建
  - WebSocket 流式问答、引用溯源、降级策略
  - 会话管理、历史记录查询、模型配置切换
- **搜索与图片能力**
  - 文本、向量、混合、高级搜索及搜索建议/历史
  - 图片上传、向量化、图文混合检索与相似度排序
  - 图片代理下载（`/api/images/file?object=...`）保障跨域与安全
- **知识图谱**
  - 自动实体提取：支持三种提取模式（系统默认类型、用户创建类型、模型自由提取）
  - 关系识别：自动识别实体间关系（属于、引用、依赖、对比、实现等）
  - 实体类型管理：支持一级、二级、三级分类层级管理
  - 图谱可视化：基于 ECharts 的交互式图谱展示（力导向、层次、圆形布局）
  - 图谱查询：支持实体搜索、关系查询、路径查找、邻居节点查询
  - 数据同步：MySQL 与 NebulaGraph 双写，支持增量同步与错误恢复
- **系统管理**
  - 知识库、分类、标签、实体类型 CRUD
  - Celery 任务监控、Redis/MinIO/NebulaGraph 配置校验
  - 完整 API 文档（100+ 个接口，含 3 个 WebSocket）

## 技术栈与目录

- **后端**
  - 框架与库：FastAPI、SQLAlchemy、Pydantic、Celery、Redis、OpenSearch 客户端、NebulaGraph Python 客户端
  - 目录重点：`app/api` 路由、`app/services` 业务服务（含 `graph_storage_service`、`entity_extraction_service`、`knowledge_graph_service`）、`app/tasks` 异步任务、`app/models` ORM 模型
  - 配置文件：`env.example`、`docker-compose.middleware.yml` 与代码配置保持一致
- **前端**
  - 框架与库：Vue 3（Composition API）、TypeScript、Vite、Element Plus、Pinia、Axios、ECharts
  - 目录重点：`src/api` 模块化接口、`src/stores` 状态管理、`src/views` 页面（含知识图谱可视化）、`src/components` 通用与业务组件、`src/utils` 工具函数、`src/composables` 组合式函数
  - WebSocket 客户端：自动重连与心跳维护，支撑多模块实时交互
  - 图谱可视化：ECharts Graph/Tree 图表，支持节点拖动、标签跟随、多布局切换

## 设计与实现对齐

- **接口统计**：16+ 个路由文件共 100+ 个接口（GET 40+、POST 40+、PUT 5+、DELETE 5+、WebSocket 3），文档管理/搜索/问答/知识图谱模块与前端 100% 对齐。
- **数据设计**：MySQL 表、OpenSearch 索引、Redis 缓存、MinIO 存储、NebulaGraph Space 结构均通过校验，索引维度（768）与 k-NN 插件配置符合向量检索需求。
- **流程图谱**：文档包含多模态问答、图片搜索、图文混合、知识图谱构建、降级策略、时序图，指导开发与调试。
- **修复记录**：2024-2025 年完成搜索接口扩展、问答路由去重、前端接口补全、图片上传与进度查询优化、知识图谱功能开发与优化。
- **新功能亮点**：
  - 知识图谱：实体提取（三种模式）、关系识别、图谱可视化、NebulaGraph 集成
  - 实体类型管理：层级分类（一级、二级、三级）、系统/用户类型区分、知识库级配置
  - 智能提取：动态 Prompt 生成、实体类型代码过滤、置信度阈值配置
- **待迭代功能**：协作类接口（如文档锁定、版本合并、系统监控等）、图谱推理查询已在设计文档列出后续迭代方向。

## 部署准备

- **通用要求**
  - 操作系统：Linux / Windows Server（推荐 Linux 服务器）
  - 基础工具：Git、Python 3.11、Node.js 16+、npm 7+（或 yarn 1.22+）、可选 Docker & Docker Compose
- **后端依赖服务**
  - MySQL 5.7+
  - OpenSearch 2.x（需安装 IK 插件）
  - Redis 6+
  - MinIO 最新版本
  - Ollama（或等价大模型服务）
  - NebulaGraph 3.x+（可选，知识图谱功能需要）

## 后端部署（`multikb-knowledge-backend`）

1. **代码准备**
   ```bash
   git clone https://github.com/ssuwwe31-commits/multikb.git
   cd multikb-knowledge-backend
   ```

2. **启动服务**
2.1  **启动中间服务**
   ```bash
   # 中间件 包括OpenSearch、Redis、MinIO、Ollama、NebulaGraph等服务 除了前后端服务
   docker compose -f docker-compose-middleware.yaml
   ```
2.2  **配置环境变量**
   ```bash
   cp env.example .env
   # 修改数据库、OpenSearch、Redis、MinIO、Ollama、NebulaGraph 等连接参数
   # 知识图谱功能需要配置 NEBULA_HOSTS、NEBULA_USER、NEBULA_PASSWORD
   ```
2.3 **初始化数据库**
   ```bash
   mysql -u <user> -p <database_name < init.sql
   ```
2.4 **启动后端服务**
   ```bash
   # 后端服务包括backend和celery两个服务
   # 启动后端服务
   docker compose -f docker-compose-backend.yaml
   ```
2.5 **启动前端服务**
   ```bash
   # 进入前端代码目录 执行 脚本即可 注意后端服务地址需要配置
   # 以下地址为后端服务默认地址 需要改成你的地址
   # BACKEND_API_URL=${1:-${BACKEND_API_URL:-http://192.168.131.158:8081}} 
   cd multikb-knowledge-frontend/
   bash deploy.sh
   ```
2.6 **其他服务(可选)**
   ```bash
   # 还需要依赖clamAV
   apt-get update
   apt-get install clamav
   ```

3. **验证**
   - 访问 `http://localhost:8000/docs` 查看 OpenAPI
   - 测试图片代理、问答流式输出等关键接口

## 前端说明（`multikb-knowledge-frontend`）

1. **环境变量配置**
   ```bash
   cp .env.example .env
   # 设置 VITE_API_BASE_URL 与 VITE_WS_BASE_URL 指向后端服务
   ```
2. **开发调试**
   ```bash
   npm run dev        # 默认端口 http://localhost:5173
   ```
3. **构建与预览**
   ```bash
   npm run build
   npm run preview    # 可选，本地预览打包结果
   ```
4. **上线部署**
   - 将 `dist/` 目录托管至 Nginx/静态服务器/CDN
   - 配置反向代理，保证 API 与 WebSocket 同源访问

## 运维与扩展建议

- **监控告警**：结合后端 `logs/`、前端性能监控与 Prometheus/Grafana 等方案，及时发现异常。
- **任务管理**：关注 Celery 队列积压，定期清理 Redis 缓存，必要时水平扩容 Workers。
- **存储安全**：MinIO 设置访问策略，配合图片代理服务控制下载权限；上传文件采用白名单校验。
- **性能调优**：合理设置 OpenSearch 索引分片、副本与 k-NN 参数，调整向量维度与召回阈值提升问答准确率；优化 NebulaGraph Space 的 partition_num 和 replica_factor 提升图谱查询性能。
- **知识图谱运维**：定期检查 NebulaGraph 同步状态，监控实体/关系数量，清理无效数据；根据知识库规模调整 Space 配置。
- **功能扩展**：基于现有接口与组件，可快速迭代多租户、权限审计、协作编辑、系统监控、图谱推理查询等高级能力。
