# 快速清理 Celery 任务元数据

## 问题

Celery Worker 启动时遇到错误：
```
ValueError: Exception information must include the exception type
```

这是因为 Redis 中存储了损坏的任务元数据。

## 快速解决方案

### 方法 1：使用清理脚本（推荐）

在**正确的 Python 环境**中（包含 redis 模块）运行：

```bash
cd multikb-knowledge-backend
python scripts/cleanup_redis_task_meta.py
```

### 方法 2：直接在 Python 中运行（如果脚本不可用）

在 Python 交互式环境中（确保在项目根目录，且已激活正确的环境）：

```python
import redis
from app.config.settings import settings

# 连接 Redis
client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)

# 查找所有任务元数据
keys = client.keys('celery-task-meta-*')
print(f"找到 {len(keys)} 个任务元数据")

# 删除所有任务元数据
if keys:
    deleted = client.delete(*keys)
    print(f"已删除 {deleted} 个任务元数据")
else:
    print("没有任务元数据需要清理")
```

### 方法 3：使用 Celery 命令（如果可用）

```bash
cd multikb-knowledge-backend
celery -A app.tasks.celery_app purge -f
```

**注意**：`celery purge` 只清理队列中的消息，不清理任务元数据。如果问题仍然存在，需要使用方法 1 或 2。

### 方法 4：手动删除特定任务（如果知道任务 ID）

如果只想删除特定的任务（例如：`f36de2cc-8bc7-40a3-93e7-505368d4b85f`）：

```python
import redis
from app.config.settings import settings

client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)

# 删除特定任务
task_id = "f36de2cc-8bc7-40a3-93e7-505368d4b85f"
key = f"celery-task-meta-{task_id}"
deleted = client.delete(key)
print(f"已删除任务: {task_id}" if deleted else "任务不存在")
```

## 清理后

清理完成后，**重启 Celery Worker**：

```bash
# 停止当前的 Celery Worker
# 然后重新启动
celery -A app.tasks.celery_app worker --loglevel=info
```

## 验证

清理后，Celery Worker 应该能正常启动，不再出现 `ValueError` 错误。
