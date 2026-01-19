# 清理 Celery 队列中的任务

## 问题说明

清理任务元数据（`celery-task-meta-*`）**不会**清理队列中的任务消息。如果队列中还有旧任务，Worker 恢复后会重新执行这些任务。

## 解决方案

### 方法 1：清理所有队列（推荐）

```bash
cd multikb-knowledge-backend
celery -A app.tasks.celery_app purge -f
```

这会清理所有队列中的任务消息。

### 方法 2：清理特定队列

```bash
# 清理代码库任务队列
celery -A app.tasks.celery_app purge -Q code -f

# 清理其他队列
celery -A app.tasks.celery_app purge -Q document -f
celery -A app.tasks.celery_app purge -Q vector -f
# ... 等等
```

### 方法 3：使用 Python 脚本清理

```python
from app.tasks.celery_app import celery_app

# 清理所有队列
celery_app.control.purge()

# 或者清理特定队列
from kombu import Queue
celery_app.control.purge(queue='code')
```

## 验证

清理后，可以通过以下命令验证队列是否为空：

```bash
# 检查队列中的消息数量
celery -A app.tasks.celery_app inspect active_queues
```

## 注意事项

1. **`purge` 会删除队列中的所有消息**，包括正在等待执行的任务
2. **不会影响正在执行的任务**，只会清理队列中的待执行任务
3. **建议在清理前停止 Worker**，避免清理过程中产生新任务

## 完整清理流程

1. **停止 Celery Worker**
2. **清理任务元数据**：
   ```bash
   python scripts/cleanup_redis_task_meta.py
   ```
3. **清理队列**：
   ```bash
   celery -A app.tasks.celery_app purge -f
   ```
4. **重启 Celery Worker**
