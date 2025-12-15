# 系统要求

> 查看 Knowledge Base 的系统要求、依赖服务和环境配置

---

## 💻 服务器要求

### 最低配置

- **CPU**：4 核
- **内存**：8GB RAM
- **存储**：50GB 可用空间
- **操作系统**：Linux（推荐 Ubuntu 20.04+ / CentOS 7+）

### 推荐配置

- **CPU**：8 核或更多
- **内存**：16GB RAM 或更多
- **存储**：100GB+ 可用空间（SSD 推荐）
- **操作系统**：Linux（Ubuntu 22.04 LTS / CentOS 8+）

### 生产环境配置

- **CPU**：16 核或更多
- **内存**：32GB RAM 或更多
- **存储**：500GB+ 可用空间（SSD 必需）
- **操作系统**：Linux（Ubuntu 22.04 LTS）
- **网络**：千兆网络，低延迟

---

## 🐍 Python 环境

### Python 版本

- **最低版本**：Python 3.9
- **推荐版本**：Python 3.10 或 3.11
- **不支持**：Python 3.8 及以下

### Python 依赖

主要 Python 包：

- FastAPI 0.104+
- SQLAlchemy 2.0+
- Celery 5.3+
- Pydantic 2.0+
- PyMySQL 1.1+
- openpyxl 3.1+
- python-docx 1.1+
- pdfplumber 0.10+
- PyMuPDF 1.23+

### 安装 Python 依赖

```bash
pip install -r requirements/base.txt
```

---

## 🗄️ 数据库要求

### MySQL

- **版本**：MySQL 8.0+ 或 MariaDB 10.6+
- **字符集**：utf8mb4
- **存储引擎**：InnoDB
- **连接数**：建议至少 100

### 数据库配置

```ini
[mysqld]
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
max_connections=200
innodb_buffer_pool_size=2G
```

### 初始化数据库

```bash
mysql -u root -p < init.sql
```

---

## 🔍 OpenSearch 要求

### OpenSearch 版本

- **版本**：OpenSearch 2.x
- **必需插件**：analysis-ik（中文分词）

### OpenSearch 配置

```yaml
# opensearch.yml
cluster.name: knowledge-base
node.name: node-1
network.host: 0.0.0.0
discovery.type: single-node

# 必需插件
plugins:
  - analysis-ik
```

### 索引配置

- **向量维度**：768（nomic-embed-text）
- **k-NN 插件**：必需启用
- **索引分片**：根据数据量调整

### 资源要求

- **内存**：至少 4GB（推荐 8GB+）
- **存储**：根据文档数量，建议 100GB+

---

## 🔴 Redis 要求

### Redis 版本

- **版本**：Redis 6.0+（推荐 Redis 7.0+）

### Redis 配置

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 用途

- **缓存**：API 响应缓存
- **任务队列**：Celery 任务队列
- **会话存储**：用户会话数据

### 资源要求

- **内存**：至少 2GB（推荐 4GB+）

---

## 📦 MinIO 要求

### MinIO 版本

- **版本**：MinIO 最新版本

### MinIO 配置

```yaml
# 存储配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=knowledge-base
```

### 用途

- **文件存储**：原始文档文件
- **图片存储**：上传的图片文件
- **备份存储**：数据备份

### 资源要求

- **存储**：根据文档数量，建议 500GB+
- **网络**：千兆网络推荐

---

## 🤖 AI 模型要求

### Ollama（LLM 服务）

- **版本**：Ollama 最新版本
- **模型**：llama2、qwen2 等
- **GPU**：推荐使用 GPU（CUDA 支持）

### 嵌入模型

- **文本嵌入**：nomic-embed-text（768维）
- **图片嵌入**：CLIP、ResNet（512维）

### OCR 模型

- **Qwen VL**：qwen2-vl:7b（推荐）
- **Tesseract**：备选方案

### Rerank 模型

- **BAAI/bge-reranker-v2-m3**：推荐使用

### GPU 要求（可选但推荐）

- **CUDA**：CUDA 11.8+
- **显存**：至少 8GB（推荐 16GB+）
- **驱动**：NVIDIA 驱动 520+

---

## 🛡️ ClamAV 要求（可选）

### ClamAV 版本

- **版本**：ClamAV 1.0+

### 连接方式

- **TCP 连接**：推荐（更稳定）
- **Socket 连接**：备选方案

### 配置

```env
CLAMAV_ENABLED=true
CLAMAV_HOST=localhost
CLAMAV_PORT=3310
CLAMAV_REQUIRED=false  # true: 强制扫描，false: 可选
```

### 资源要求

- **内存**：至少 2GB
- **更新**：需要定期更新病毒库

---

## 🌐 网络要求

### 端口要求

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | 后端 API 服务 |
| Celery Worker | - | 异步任务处理 |
| MySQL | 3306 | 数据库 |
| OpenSearch | 9200 | 搜索引擎 |
| Redis | 6379 | 缓存和队列 |
| MinIO | 9000 | 对象存储 |
| Ollama | 11434 | LLM 服务 |
| ClamAV | 3310 | 病毒扫描（可选） |

### 防火墙配置

```bash
# 开放必要端口
sudo ufw allow 8000/tcp
sudo ufw allow 3306/tcp
sudo ufw allow 9200/tcp
sudo ufw allow 6379/tcp
sudo ufw allow 9000/tcp
```

---

## 🐳 Docker 要求（可选）

### Docker 版本

- **Docker**：Docker 20.10+
- **Docker Compose**：Docker Compose 2.0+

### 使用 Docker 部署

```bash
# 使用 Docker Compose 一键部署
docker-compose up -d
```

---

## ☸️ Kubernetes 要求（可选）

### Kubernetes 版本

- **Kubernetes**：1.24+
- **Helm**：3.8+（如果使用 Helm）

### 资源配额

```yaml
resources:
  requests:
    cpu: 4
    memory: 8Gi
  limits:
    cpu: 8
    memory: 16Gi
```

---

## 📋 环境变量配置

### 必需配置

```env
# 应用配置
APP_NAME=SPX Knowledge Base
DEBUG=false
SECRET_KEY=your-secret-key-here

# 数据库
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/spx_knowledge

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenSearch
OPENSEARCH_URL=http://localhost:9200

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 可选配置

```env
# ClamAV（可选）
CLAMAV_ENABLED=true
CLAMAV_HOST=localhost
CLAMAV_PORT=3310

# OCR（可选）
OCR_ENGINE=qwen_vl
OLLAMA_OCR_MODEL=qwen2-vl:7b

# Rerank（可选）
RERANK_ENABLED=true
RERANK_MODEL_NAME=BAAI/bge-reranker-v2-m3

# 文件限制
MAX_FILE_SIZE=104857600  # 100MB
ALLOWED_FILE_TYPES=.docx,.pdf,.txt,.log
```

---

## ✅ 环境检查清单

### 安装前检查

- [ ] Python 3.9+ 已安装
- [ ] MySQL 8.0+ 已安装并运行
- [ ] OpenSearch 2.x 已安装并运行
- [ ] Redis 6.0+ 已安装并运行
- [ ] MinIO 已安装并运行
- [ ] Ollama 已安装并运行
- [ ] 所有端口已开放
- [ ] 防火墙配置正确

### 配置检查

- [ ] 环境变量已配置
- [ ] 数据库已初始化
- [ ] OpenSearch 索引已创建
- [ ] MinIO 存储桶已创建
- [ ] 模型已下载

### 功能检查

- [ ] API 服务正常启动
- [ ] Celery Worker 正常运行
- [ ] 文档上传功能正常
- [ ] 问答功能正常
- [ ] 搜索功能正常

---

## 🔧 常见问题

### Q: 可以使用 PostgreSQL 替代 MySQL 吗？

A: 目前仅支持 MySQL/MariaDB，PostgreSQL 支持计划中。

### Q: 必须使用 GPU 吗？

A: 不是必需的，但使用 GPU 可以显著提升性能，特别是 LLM 推理和向量化。

### Q: ClamAV 是必需的吗？

A: 不是必需的，但强烈推荐在生产环境启用。

### Q: 最小化部署需要哪些服务？

A: 最小化部署需要：MySQL、OpenSearch、Redis、MinIO、Ollama。

---

**下一步**：
- [快速开始指南](./getting-started.md)
- [Docker 部署指南](./docker-deployment.md)
- [Kubernetes 部署指南](./kubernetes-deployment.md)

