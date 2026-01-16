# 🚀 Celery Worker 启动说明

## 快速启动

在 `celery_worker` 目录下直接运行：

```bash
cd multikb-knowledge-backend/celery_worker
python app.py
```

这将自动启动：
- ✅ **Celery Worker** - 处理所有异步任务
- ✅ **Celery Beat** - 定时任务调度器（如果启用）
- ✅ **健康检查服务** - HTTP 服务（端口 8010）

---

## 📋 监听的队列

默认监听以下队列：

- `document` - 文档处理任务
- `vector` - 向量化任务
- `index` - 索引任务
- `image` - 图片处理任务
- `version` - 版本管理任务
- `cleanup` - 清理任务
- `notification` - 通知任务
- `security_scan` - 安全扫描任务
- `code` - **代码库分析任务（包括 Agent 分析）** ⭐
- `celery` - 默认队列
- `observability` - 可观测性任务（如果启用）

---

## 🔧 配置选项

### 环境变量

```bash
# 日志级别
CELERY_LOG_LEVEL=INFO|DEBUG

# 并发数
CELERY_CONCURRENCY=4

# 监听的队列（逗号分隔）
CELERY_QUEUES=document,vector,index,code,celery

# 是否自动启动 Worker（默认 true）
CELERY_AUTOSTART=true
```

### Settings 配置

在 `.env` 或 `settings.py` 中配置：

```python
CELERY_LOG_LEVEL=INFO
CELERY_CONCURRENCY=4
CELERY_QUEUES=document,vector,index,code,celery
OBSERVABILITY_ENABLE_SCHEDULE=true  # 是否启用 observability 队列
```

---

## 🎯 代码库任务（code 队列）

### 支持的任务

- ✅ `tasks.code_repository_tasks.clone_and_analyze` - 克隆并分析代码库
- ✅ `tasks.code_repository_tasks.update_repository` - 更新代码库
- ✅ `tasks.code_repository_tasks.analyze_with_agent` - **Agent 分析代码库** ⭐
- ✅ `tasks.code_repository_tasks.cleanup_old_repositories` - 清理旧仓库

### 使用示例

```python
from app.tasks.celery_app import celery_app

# 提交 Agent 分析任务
task = celery_app.send_task(
    'tasks.code_repository_tasks.analyze_with_agent',
    args=[repo_id, use_cache],
    queue='code'
)
```

---

## 🔍 健康检查

启动后，可以通过 HTTP 接口检查服务状态：

```bash
curl http://localhost:8010/health
```

响应：
```json
{
  "service": "celery-worker",
  "status": "ok",
  "redis_url": "redis://localhost:6379/0"
}
```

---

## 📊 日志

日志文件位置：
- `logs/celery.log` - Celery Worker 主日志
- `celery_tasks.log` - 任务执行日志

---

## 🐛 故障排查

### 问题 1：Worker 无法启动

**检查**：
1. Redis 是否运行：`redis-cli ping`
2. 队列配置是否正确
3. 查看日志：`logs/celery.log`

### 问题 2：任务一直处于 PENDING 状态

**检查**：
1. Worker 是否正在运行
2. Worker 是否监听正确的队列
3. 任务队列名称是否匹配

### 问题 3：Agent 分析任务未执行

**检查**：
1. 确认 `code` 队列在监听列表中
2. 检查任务是否正确提交到 `code` 队列
3. 查看任务日志：`logs/celery_tasks.log`

---

## 💡 最佳实践

1. **生产环境**：使用 systemd 或 supervisor 管理进程
2. **开发环境**：直接运行 `python app.py` 即可
3. **监控**：定期检查健康检查接口和日志文件

---

## 📝 注意事项

- Worker 会自动根据 CPU 核心数计算并发数
- Windows 使用 `solo` 池，Linux 使用 `prefork` 池
- Beat 调度器使用 Redis 锁确保只有一个实例运行

---

**版本**: v1.1  
**更新日期**: 2026-01-14  
**状态**: ✅ 已支持代码库任务和 Agent 分析
