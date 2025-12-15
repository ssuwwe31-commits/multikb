# 实现方案与优化指南

> 本文档整合了变更追踪、存储方案选择、大规模数据优化等实现细节和优化建议

## 1. 变更关联分析实现方案

### 1.1 变更记录获取方式

**混合方案**（推荐）：
1. **自动获取（优先）**：
   - ✅ 基于现有 `resource_events` 表：自动追踪 K8s 资源变更（Deployment、ConfigMap、Secret、Pod）
   - ✅ 基于现有 `resource_snapshots` 表：对比历史快照，识别配置变更
   - ⚠️ 可选：集成 CI/CD 系统（Jenkins、GitLab CI、GitHub Actions）获取部署变更
   - ⚠️ 可选：集成 Git 系统获取代码变更

2. **手动提供（补充）**：
   - 诊断时在 `trigger_payload.recent_changes` 中提供变更信息
   - 诊断后通过 API 补充变更信息

### 1.2 变更追踪机制

系统已经实现了**实时变更追踪**机制：

1. **Watch 机制（实时）**：
   - 使用 K8s Watch API (`watch=true&resourceVersion=xxx`)
   - 实时监听资源变更事件（ADDED、MODIFIED、DELETED）
   - 变更发生时立即记录
   - 通过 `resource_version` 实现增量同步，不会丢失变更

2. **定时全量同步（补充）**：
   - Celery Beat 定时任务：`sync_active_clusters`
   - 同步间隔：`OBSERVABILITY_SYNC_INTERVAL_SECONDS`（可配置）
   - 作用：确保数据一致性，处理 Watch 连接断开的情况

3. **手动触发同步**：
   - API：`POST /api/v1/observability/clusters/{cluster_id}/sync`

**关键点**：
- ✅ **不是定期获取**，而是**实时 Watch + 定时补充**
- ✅ 变更发生时立即记录，无需等待定时任务
- ✅ 诊断时直接查询已记录的变更

### 1.3 实施步骤（分阶段）

**阶段1（立即）**：基于现有 K8s 资源变更追踪
- 查询 `resource_events` 表（或 OpenSearch 索引）
- 查询 `resource_snapshots` 表
- 在诊断流程中集成

**阶段2（1周内）**：支持手动提供变更信息
- 扩展诊断 API
- 创建变更管理 API

**阶段3（按需）**：可选集成 CI/CD 和 Git 系统

## 2. 存储方案选择

### 2.1 推荐方案：混合存储 ⭐

**resource_snapshots → MySQL**（保留）
- 关系型数据，需要事务支持
- 每个资源一条记录，数据量相对较小

**resource_events → OpenSearch**（推荐迁移）
- 时间序列数据，查询为主
- 适合大规模数据，查询性能优秀

### 2.2 OpenSearch 优势

| 对比项 | MySQL | OpenSearch |
|--------|-------|------------|
| 查询性能（3000万条） | 100-500ms | 10-50ms ⭐ |
| JSON 字段查询 | 一般 | 优秀 ⭐ |
| 时间序列查询 | 一般 | 优秀 ⭐ |
| 水平扩展 | 困难 | 容易 ⭐ |
| 自动数据清理 | 需手动 | ILM 自动 ⭐ |
| 存储空间 | 60GB | 40-50GB ⭐ |

### 2.3 实施策略：双写

1. 新事件同时写入 MySQL 和 OpenSearch
2. 查询优先使用 OpenSearch
3. MySQL 作为备份，可以逐步迁移

## 3. 大规模数据优化

### 3.1 数据量分析

**假设场景**：100 万个 Pod，每个 Pod 每天 1 次变更

**数据量估算**：
- `resource_snapshots` 表：约 11.6GB（每个资源一条记录，不会无限增长）
- `resource_events` 表：**100万条/天 × 30天 = 3000万条 ≈ 60GB**（会持续增长）

### 3.2 优化方案

#### 如果使用 MySQL：
1. **数据保留策略**（必须）：
   - 自动清理 30 天以上的事件
   - 定时任务每天执行
   - 数据量控制在 3000万条以内

2. **查询优化**（必须）：
   - 只查询指定资源的变更（不查询整个集群）
   - 限制返回数量（最多 100 条）
   - 优化索引

3. **分级保留策略**（推荐）：
   - 最近 7 天：完整保留
   - 7-30 天：只保留重要变更（created、deleted、spec 变更）

**预期效果**：
- 数据量：从 730GB/年 降低到 27.8GB/30天（分级保留）
- 查询性能：< 50ms

#### 如果使用 OpenSearch（推荐）⭐：
1. **索引生命周期管理（ILM）**（自动）：
   - 自动清理 30 天以上的数据
   - 无需手动清理任务
   - 数据量自动控制

2. **查询优化**（内置）：
   - 时间序列查询优化
   - 自动索引，查询性能优秀
   - 支持复杂查询和聚合

3. **水平扩展**（内置）：
   - 支持分片，自动扩展
   - 适合大规模数据

**预期效果**：
- 数据量：自动管理，30 天数据约 40-50GB（压缩存储）
- 查询性能：< 10-50ms（比 MySQL 快 10-50 倍）
- 扩展性：支持水平扩展，适合百万级数据

## 4. 实施优先级

### P0（立即实施）：
1. ⭐ **基于现有 K8s 资源变更追踪**
   - 创建 OpenSearch 索引（推荐）或使用 MySQL
   - 修改事件记录逻辑（双写策略）
   - 创建变更查询服务
   - 在诊断流程中集成

2. ⭐ **数据保留策略**（必须）
   - **如果使用 OpenSearch**：实施 ILM 自动清理（推荐）
   - **如果使用 MySQL**：实施自动清理机制
   - 配置保留天数（默认 30 天）

3. ⭐ **查询优化**（必须）
   - 限制查询范围（只查询指定资源）
   - 限制返回数量（最多 100 条）

### P1（1周内）：
4. **支持手动提供变更**
   - 扩展诊断 API
   - 创建变更管理 API

5. **分级保留策略**（如果使用 MySQL）

### P2（按需）：
6. **集成 CI/CD 系统**（如果用户有需求）
7. **集成 Git 系统**（如果用户有需求）
8. **数据归档和分区表**（如果数据量仍然很大）

## 5. 关键配置

### 5.1 OpenSearch 索引配置

```python
# app/config/settings.py
RESOURCE_EVENTS_INDEX_NAME: str = "resource_events"
RESOURCE_EVENTS_RETENTION_DAYS: int = 30
```

### 5.2 数据保留配置

```python
# 小规模集群（< 1万 Pod）
OBSERVABILITY_EVENT_RETENTION_DAYS = 90

# 中规模集群（1-10万 Pod）
OBSERVABILITY_EVENT_RETENTION_DAYS = 30
OBSERVABILITY_EVENT_TIERED_RETENTION = True

# 大规模集群（> 10万 Pod）
OBSERVABILITY_EVENT_RETENTION_DAYS = 7
OBSERVABILITY_EVENT_TIERED_RETENTION = True
OBSERVABILITY_EVENT_ARCHIVE_ENABLED = True
```

