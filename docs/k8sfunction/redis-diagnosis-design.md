# Redis 诊断设计说明（主从 / 哨兵 / 集群）

> 目标：在现有“K8s 统一诊断流程”基础上，为 Redis 集群补充专用的 **SLI/SLO、标准问题类型、规则集与 LLM Prompt 设计**，实现更精准的问题诊断。

---

## 1. 场景与部署形态

### 1.1 典型部署形态

- **单实例模式**
  - 形态：`Deployment + Service`
  - 使用场景：缓存为主、容忍短暂不可用、非强一致性要求。

- **主从模式**
  - 形态：`StatefulSet（master/slave）+ Service`
  - 区分角色：通过 `labels/annotations` 标记 `middleware.type=redis`，`middleware.role=master/slave`。
  - 要求：主从复制稳定，故障时可手工或通过哨兵切换。

- **哨兵（Sentinel）模式**
  - 形态：额外部署 Sentinel Pod（`Deployment/StatefulSet`），监控 master/slave，自动完成故障转移。
  - 标记：`middleware.type=redis_sentinel` 或 `middleware.role=sentinel`。

- **集群模式（Redis Cluster）**
  - 形态：多个 Pod 组成 Redis Cluster，通过 slot 分布实现水平扩展。
  - 节点角色：master/slave，slot 分配信息由 Redis 自身维护。

### 1.2 诊断入口

- 入口资源类型：
  - Pod：`resource_type="pods"`（常见告警直接落在 Pod 上）
  - StatefulSet/Deployment：`resource_type="statefulsets"/"deployments"`（集群整体异常时）
- 中间件识别：
  - 通过 `labels` 或 `annotations`：
    - `middleware.type=redis`（或 redis_sentinel / redis_cluster）
    - `middleware.role=master/slave/sentinel`

---

## 2. Redis 的 SLI / SLO 与关键指标（建议）

> 当前版本以 K8s + 日志 + 基础资源指标为主，后续按需接入 Redis Exporter 指标。

### 2.1 SLI 维度与指标映射（对齐业界实践）

| 维度 | 建议 SLI | 典型指标示例（如接入 Exporter） | K8s 视角可用信号 |
|------|----------|--------------------------------|------------------|
| 可用性 | 成功请求比例 / 错误率 | `redis_commands_processed_total` 与错误计数比值 | Pod 重启、健康探针失败、应用侧大量 Redis 调用失败 |
| 性能 | 请求延迟（p95/p99） | 应用侧 Redis 调用延迟、慢日志统计 | Node/Pod CPU 飙高、日志中慢命令/超时 |
| 容量 | 内存使用率 / 命中率 | `used_memory` / `maxmemory`，`keyspace_hits/misses` | Pod 内存接近 Request/Limit、OOM/evict 日志 |
| 连接 | 并发连接数 / 连接失败率 | `connected_clients`、连接错误计数 | 日志 `Too many connections`、应用连接失败 |

### 2.2 推荐阈值与告警分级（示例）

> 阈值可按环境调优，这里给出参考值，用于形成统一的告警/诊断基线。

- **连接数 / maxclients**  
  - `connected_clients / maxclients >= 0.8`：P2 告警（告警但暂不影响业务）  
  - `>= 0.9`：P1 告警（需要运维在 15 分钟内关注：限流/扩容/排查短连接）  
  - 达到上限且日志出现 `Too many connections` / `max number of clients reached`：P0（`redis.connection_exhausted`）

- **内存使用率 / maxmemory**  
  - `used_memory / maxmemory >= 0.8`：P2 告警（容量趋紧，需规划）  
  - `>= 0.9`：P1 告警（短期内可能 OOM/大量淘汰）  
  - 日志出现 `OOM command not allowed` 或大量 eviction：P0（`redis.memory_exhausted`）

- **持久化 / 存储**  
  - PVC/Node 事件 `No space left on device` / `Filesystem read-only`：P0（`redis.persistent_storage_issue`）  
  - Redis 日志出现 AOF/RDB 写失败：视影响范围通常也视为 P0。

- **高可用 / 复制 / 哨兵**  
  - Master 长时间不可达 / 从节点持续复制失败：P0（`redis.master_unreachable`）  
  - Sentinel 在短时间内多次 failover / 频繁切主：P1~P0（`redis.sentinel_failover_unstable`，根据业务受影响程度）。

上述阈值与告警级别可以映射到 Prometheus 告警规则（接入 Exporter 时），也可以在目前仅有 K8s + 日志的场景中作为 LLM/规则的判断依据和文字提示。

### 2.3 短期实现策略

- 先使用：
  - Node/Pod 资源指标（CPU/内存、重启次数）；
  - Redis Pod 日志；
  - PVC/Node 事件（存储相关问题）。
- 在规则中通过“日志 + 资源指标 + K8s 事件”组合，近似判断上述 SLI 是否明显异常。

---

## 3. 标准问题类型设计

为便于规则与 LLM 复用，定义一组标准问题编码：

- **`redis.memory_exhausted`**  
  内存耗尽 / 频繁 OOM / 大量 key 被淘汰。

- **`redis.connection_exhausted`**  
  连接数耗尽 / Too many connections / maxclients 达上限。

- **`redis.master_unreachable`**  
  主节点不可达 / 主从复制中断（主从模式、集群模式）。

- **`redis.sentinel_failover_unstable`**  
  哨兵故障转移不稳定 / 频繁触发 failover / 反复切主。

- **`redis.cluster_slot_misconfigured`**  
  集群 slot 分布异常 / 某些节点下线导致路由错误（MOVED/ASK 错误显著增多）。

- **`redis.persistent_storage_issue`**  
  与 PVC/磁盘相关的问题：只读文件系统、磁盘空间不足、IO 异常对持久化造成影响。

每个问题类型绑定信息（用于规则和 LLM 输出统一）：

- `code`：问题编码（如 `redis.memory_exhausted`）  
- `title`：问题标题（简短、面向运维）  
- `description`：问题详细说明  
- `severity`：严重级别（对应 P0/P1/P2/P3）  
- `recommended_actions`：建议操作步骤列表（可挂知识库/Runbook ID）  
- `alert_level`：建议告警等级（P0/P1/P2/P3）

示例（抽象结构）：

```json
{
  "code": "redis.memory_exhausted",
  "title": "Redis 内存耗尽 / 频繁 OOM",
  "severity": "critical",
  "alert_level": "P0",
  "description": "Redis 内存使用接近或超过 maxmemory，出现 OOM 或大量 key 淘汰，可能导致请求失败或数据丢失。",
  "recommended_actions": [
    "短期：对高流量业务限流或降级，临时扩容实例或提升资源规格。",
    "中期：调整 maxmemory 策略（如 volatile-lru）、优化 key 过期策略，减少大 key。",
    "长期：做容量规划，引入分片/集群或增强缓存命中率。"
  ]
}
```

---

## 4. 规则引擎设计（`evaluate_redis_rules`）

### 4.1 输入数据

- `context`：包含 cluster_id、namespace、resource_name、role 等；
- `api_data`：来自 API Server 的 Pod/StatefulSet/Node/PVC 状态；
- `metrics`：当前时间段的 CPU/内存/重启率等数据；
- `logs`：Redis Pod 日志（结构化后的 `logs` 数组）；
- `change_events`（可选）：近 24 小时配置变更（StatefulSet/ConfigMap/Secret）。

### 4.2 规则示意

#### 4.2.1 资源 / 内存问题（`redis.memory_exhausted`）

- 条件示例：
  - Node 或 Pod 内存利用率长时间接近 100%；
  - Redis 日志中出现：
    - `OOM command not allowed`
    - 大量 key eviction 相关日志（如 `evicted` 关键字）
  - Pod 在短时间内重启多次。

#### 4.2.2 连接数问题（`redis.connection_exhausted`）

- 条件示例：
  - Redis 日志中出现：
    - `max number of clients reached`
    - `Too many connections`
  - 应用侧或代理层日志中 Redis 连接失败/超时显著增多（可选）。

#### 4.2.3 主从 / 复制问题（`redis.master_unreachable`）

- 条件示例：
  - 从节点日志中存在：
    - `Master not reachable`
    - 持续的复制错误日志；
  - StatefulSet/Pod 事件中显示主节点频繁重启或 NotReady。

#### 4.2.4 哨兵不稳定（`redis.sentinel_failover_unstable`）

- 条件示例：
  - Sentinel Pod 日志频繁出现：
    - `+failover-state-*` 反复变化；
    - 多次在短时间内切主；
  - 多个应用 Pod 的 Redis 连接目标 IP/主机在短时间内来回变化。

#### 4.2.5 集群 slot / 节点问题（`redis.cluster_slot_misconfigured`）

- 条件示例：
  - Redis/客户端日志中 `MOVED`/`ASK` 错误量在短时间内激增；
  - 某些 Redis 节点 Pod NotReady 或 CrashLoopBackOff；
  - ConfigMap/StatefulSet 等存在近期 slot/节点相关配置变更。

#### 4.2.6 存储 / 持久化问题（`redis.persistent_storage_issue`）

- 条件示例：
  - PVC/Node 事件中出现：
    - `Filesystem read-only`
    - `No space left on device`
  - Redis 日志中存在 AOF/RDB 写失败或持久化错误；
  - Pod 有较多 CrashLoopBackOff，与磁盘/持久化相关。

### 4.3 规则输出结构

规则函数 `evaluate_redis_rules(...)` 返回类似结构：

```json
[
  {
    "code": "redis.memory_exhausted",
    "severity": "critical",
    "alert_level": "P0",
    "description": "Redis 内存耗尽，出现 OOM 或大量 key 淘汰",
    "evidence": {
      "node_memory": "95%",
      "pod_memory": "90%",
      "log_snippets": ["OOM command not allowed ..."]
    }
  }
]
```

这些 `findings` 会被写入 `diagnosis_memories`（memory_type="rule"），并同时作为 LLM 输入的一部分。

---

## 5. LLM Prompt 设计（Redis 专用补充）

### 5.1 触发条件

- 在 LLM 调用前，若从 `context` 或 `api_data` 中识别出：
  - `middleware.type=redis`（或 redis_sentinel/redis_cluster）；
  - 则在构造 Prompt 时追加 Redis 专用说明。

### 5.2 Prompt 补充内容（示意）

在通用 Prompt 的「输入信息」部分后，追加：

1. **部署模式与角色说明**：
   - 当前诊断对象：Redis（单机 / 主从 / 哨兵 / 集群），角色（master/slave/sentinel）。
2. **重点关注点提示**：
   - 检查内存使用与配置：
     - 是否接近 `maxmemory`，是否频繁出现 OOM 或大量 key 淘汰；
   - 检查连接情况：
     - 并发连接数是否接近上限，是否存在大量连接失败/超时；
   - 检查主从复制与哨兵：
     - 是否有主节点不可达、复制中断、哨兵反复触发 failover；
   - 检查集群 slot/节点状态：
     - 是否有节点下线、slot 迁移失败，客户端是否频繁收到 MOVED/ASK 错误；
   - 检查近期配置/版本变更：
     - ConfigMap/StatefulSet/Secret 是否最近修改了 maxmemory/maxclients/持久化策略/镜像版本等。
3. **标准问题类型枚举提示**：
   - 告诉 LLM 常见问题类型编码：
     - `redis.memory_exhausted`
     - `redis.connection_exhausted`
     - `redis.master_unreachable`
     - `redis.sentinel_failover_unstable`
     - `redis.cluster_slot_misconfigured`
     - `redis.persistent_storage_issue`
   - 要求：在分析结论中指出最可能的问题类型编码，并给出置信度。

4. **告警等级与运维优先级提示**：
   - 告诉 LLM 当前相关指标已触发的阈值档位（如“内存使用率 92%，落在 90% 阈值以上”）；  
   - 告诉 LLM 推荐的告警等级（P0/P1/P2），要求在结论中给出“处理优先级建议”（例如“需要立即处理 / 15 分钟内处理 / 可以在低峰期处理”）。

### 5.3 输出要求补充

在原有结构化 JSON 输出基础上，增加字段：

```json
{
  "redis_problem_type": "redis.memory_exhausted",
  "redis_problem_confidence": 0.9,
  "redis_alert_level": "P0"
}
```

并在 `solutions` 中给出：

- 立即缓解措施（如临时限流、扩容、降低数据量）；
- 根本解决措施（如优化 maxmemory 策略、连接池配置、集群拓扑设计）；
- 预防措施（如增加监控告警、容量规划等）。

---

## 6. 迭代与实现优先级

- **P0（当前可做）**
  - 基于现有日志 + K8s 指标，先实现 `evaluate_redis_rules` 的简化版本；
  - 在 LLM Prompt 中增加 Redis 类型与问题类型枚举的说明；
  - 将 LLM 输出中的 `redis_problem_type` 与知识库/Runbook 做简单映射。

- **P1（接入 Redis Exporter 后）**
  - 引入 Redis 专用指标（connected_clients、used_memory、hits/misses 等），细化规则；
  - 为主从、哨兵、集群模式分别补充更细的规则与 Prompt 提示。

-- **P2（可选，更深集成）**
  - 在不越过安全边界的前提下，引入有限的 Redis 管理命令调用（如 `INFO`、`CLUSTER INFO`），增强诊断精度；
  - 与 CI/CD/Git 变更记录结合，精确定位“版本/配置变更 → 故障”的因果关系。

---

## 7. 告警规则与诊断流程触发设计

> 目标：将 Prometheus/Alertmanager 等告警体系与本诊断模块联动，实现“满足一定条件自动触发 Redis 诊断流程”。

### 7.1 告警 → 诊断的总体流程

1. 指标监控与告警规则配置（Prometheus + redis_exporter / Node Exporter 等）；  
2. 告警事件由 Alertmanager 推送到平台（`/api/v1/observability/alerts/webhook`）；  
3. 后端解析告警标签（cluster/namespace/pod/service 等），映射到目标 Redis 实例或 StatefulSet；  
4. 调用 `DiagnosisService.trigger_diagnosis()` 启动诊断流程；  
5. 诊断结果（根因 + 解决方案 + Redis 问题类型 + 告警等级建议）回写到告警详情或通知渠道。

### 7.2 告警规则示例（Prometheus 视角，示意）

> 以下为示例规则，具体 PromQL 需根据实际指标命名和 redis_exporter 配置调整。

- **连接数告警（对应 `redis.connection_exhausted`）**

```json
groups:
  - name: redis-connection-rules
    rules:
      - alert: RedisConnectionsHigh
        expr: redis_connected_clients / redis_config_maxclients > 0.9
        for: 1m
        labels:
          severity: critical
          component: redis
          redis_problem_type: redis.connection_exhausted
        annotations:
          summary: "Redis 连接数接近上限 ({{ $labels.instance }})"
          description: "connected_clients/maxclients > 90%，可能导致新的连接被拒绝。"
```

- **内存使用告警（对应 `redis.memory_exhausted`）**

```json
  - alert: RedisMemoryHigh
    expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
    for: 5m
    labels:
      severity: critical
      component: redis
      redis_problem_type: redis.memory_exhausted
    annotations:
      summary: "Redis 内存使用率过高 ({{ $labels.instance }})"
      description: "used_memory/maxmemory > 90%，有发生 OOM 或大量 key 淘汰的风险。"
```

- **持久化/磁盘问题告警（对应 `redis.persistent_storage_issue`）**

> 可通过 Node 磁盘指标 + K8s 事件综合设置告警，这里只在设计层面说明，不列出具体 PromQL。

### 7.3 告警到诊断触发的映射策略

在接收告警的 Webhook 处理逻辑中（见 `k8s-monitoring-design.md` 告警集成章节），按以下规则触发诊断：

- **触发条件（示例）**
  - `labels.component = "redis"` 且 `severity in ("warning", "critical")`；  
  - 或 `annotations.redis_problem_type` 存在（上游规则已分类）。

- **资源定位**
  - 通过告警中的 `labels`（如 `namespace`、`pod`、`statefulset`、`service` 等）定位到：
    - 诊断入口资源（优先 Pod，其次 StatefulSet/Deployment）；  
    - 对应的 `cluster_id`（通过集群配置表映射）。

- **诊断触发参数（示例）**

```json
POST /api/v1/observability/diagnosis/run
{
  "cluster_id": 1,
  "namespace": "prod",
  "resource_type": "pods",
  "resource_name": "redis-master-0",
  "trigger_source": "alert",
  "trigger_payload": {
    "alertname": "RedisMemoryHigh",
    "severity": "critical",
    "redis_problem_type_hint": "redis.memory_exhausted"
  }
}
```

- **触发策略建议**
  - P0 告警（如 `redis_memory_exhausted`、`redis_persistent_storage_issue`）：
    - 默认自动触发诊断流程；
    - 支持配置“是否自动触发”开关。
  - P1 告警（如连接数高但尚未完全耗尽）：
    - 可配置为自动触发或仅提示“可一键触发诊断”；
  - P2/P3 告警：
    - 一般只用于趋势性预警，是否自动触发可由用户策略决定。

### 7.4 诊断结果与告警的联动

- 诊断完成后，记录的字段中包括：
  - `redis_problem_type`（如 `redis.memory_exhausted`）  
  - `redis_problem_confidence`（0~1）  
  - `redis_alert_level`（建议的处理优先级，P0/P1/P2）  
  - 结构化 `solutions`（立即缓解、根本解决、预防措施）

- 可选联动方式：
  - 在告警详情页展示“自动诊断结果”；  
  - 将诊断结论回写到告警平台（如 Alertmanager 注解、IM 通知消息）；  
  - 将诊断结果沉淀为知识库条目，用于后续相似告警的快速定位。

---

> 本文档作为 Redis 诊断的专用设计说明，后续实现时可按 P0 → P1 → P2 逐步落地，并与 `k8s-monitoring-design.md`、`middleware-diagnosis-design.md` 以及告警规则体系保持一致。***

