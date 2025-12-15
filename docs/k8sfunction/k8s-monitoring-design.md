# K8s 运维诊断平台功能设计说明

## 1. 目标概述

**核心目标**：通过接入 K8s API Server、监控系统、日志系统，自动排查 K8s 集群中的任何问题。

**三个数据源**：
1. **K8s API Server**：获取资源状态、配置、事件
2. **监控系统（Prometheus）**：获取指标数据
3. **日志系统（ELK/Loki）**：获取日志数据

**统一诊断流程**：
- 所有资源类型（Pod、Node、Deployment、Service 等）用**同一套诊断流程**
- 不同资源类型**收集不同的数据**（但流程相同）
- 根据资源类型，自动决定收集哪些数据

**设计原则**：
- ✅ **统一性**：统一流程、统一接口、统一数据结构
- ✅ **可扩展性**：易于添加新资源类型、新规则、新数据源
- ✅ **简单性**：流程简单清晰，不要过度设计

---

## 1.1 系统是做什么的？（快速理解）

**一句话说明**：当 K8s 集群出现问题时（Pod、Node、Deployment、Service 等任何资源），系统自动收集数据、分析原因、给出解决方案。

**支持的资源类型**：
- **Pod**：容器运行问题（CPU高、内存溢出、频繁重启等）
- **Node**：节点资源、状态问题（NotReady、资源不足、磁盘满等）
- **Deployment/StatefulSet**：工作负载管理问题（副本数异常、滚动更新失败等）
- **Service**：服务发现问题（无法访问、Endpoints为空等）
- **ConfigMap/Secret**：配置管理问题（配置不存在、格式错误等）
- **NetworkPolicy**：网络策略问题（流量被阻止、策略冲突等）
- **ResourceQuota**：资源配额问题（配额超限、无法创建资源等）
- **PVC**：存储问题（存储不足、挂载失败等）

**诊断流程（简化版）**：
```
问题出现
  ↓
收集数据（API Server + 监控系统 + 日志系统）
  ↓
规则检测（检测已知问题模式）
  ↓
AI分析（基于实际数据，直接分析问题，给出置信分）⭐【核心改进】
  ↓
如果置信分 >= 0.8 → 完成诊断
如果置信分 < 0.8 → 继续执行后续步骤
  ↓
查知识库（以前遇到过吗？）
  ↓
扩展K8s信息收集（如果知识库没有高置信度结果）
  ↓
外部搜索（如果AI和知识库都不确定，联网搜索）
  ↓
给出结论（根因 + 解决方案）
  ↓
如果经过8个步骤后仍不确定，申请人工介入
```

**准确率评估**：
- 简单问题（规则检测 + 知识库）：**80-90%**
- 中等问题（需要AI推理）：**65-75%**
- 复杂问题（经过8个步骤后仍无法判断，需人工介入）：**50-65%**
- **总体：70-80%**（改进后预期：75-85%）

## 2. 系统角色与边界
- **平台服务（控制面）**：部署在集群外部或内部，统一调度、存储与分析数据；暴露 API 给运维工具或 CLI。
- **Kubernetes 集群**：提供资源元数据、事件、实时状态；通过 RBAC 控制访问范围。
- **监控系统（Prometheus）**：提供时序指标并负责规则评估，是监控与告警的核心。
- **告警系统（Alertmanager / Prometheus Alerting 组件 / 第三方）**：承接 Prometheus 的告警通知并分发给平台，触发自动分析流程。
- **日志系统（容器 stdout/stderr 聚合 + ELK/Loki 等）**：集中收集 Pod 日志或应用日志，供异常分析时回溯细节。

## 3. 数据采集与接口

### 3.1 Kubernetes API Server（资源信息获取）
- **访问方式**：直接通过 HTTP REST API 调用 Kubernetes API Server，**不是通过 kubectl 命令**。
  - 认证方式：`Bearer Token` / `kubeconfig` / `ServiceAccount` / 客户端证书。
  - API 地址：`https://<api-server>:6443`
- **获取内容**：
  - **Pod 配置信息**：通过 `GET /api/v1/namespaces/{namespace}/pods/{name}` 获取 Pod 的完整定义（spec、metadata、labels、annotations 等）。
  - **Pod 状态信息**：通过上述接口返回的 `status` 字段获取 Pod 当前状态（phase、conditions、containerStatuses 等）。
  - **其他资源**：`Deployment`、`ReplicaSet`、`StatefulSet`、`Node`、`Event`、`ConfigMap`、`Secret` 等。
- **采集模式**：
  - **轮询同步（List）**：定时调用 `GET /api/v1/namespaces/{namespace}/pods` 拉取全量资源列表，适配缓存与比对。
  - **Watch 订阅**：使用 `GET /api/v1/namespaces/{namespace}/pods?watch=true&resourceVersion={version}` 实时感知资源变更，触发增量更新。
- **实现细节**：
  - 使用 `httpx` 库直接发送 HTTP 请求到 API Server。
  - 请求头包含 `Authorization: Bearer <token>` 进行认证。
  - 支持 `resourceVersion` 参数实现增量同步。
  - 将获取的资源信息保存到本地数据库（`resource_snapshots` 表），便于快速查询和比对。
- **数据标准化**：为资源对象增加统一标签（集群 ID、命名空间、所属服务等），便于与监控/告警关联。

### 3.2 Prometheus
- 访问方式：HTTP API (`/api/v1/query`、`/api/v1/query_range`)。
- 常用指标：
  - 容器 CPU：`container_cpu_usage_seconds_total`
  - 容器内存：`container_memory_usage_bytes`
  - Pod 重启次数：`kube_pod_container_status_restarts_total`
  - Pod 状态：`kube_pod_status_phase` / `kube_pod_status_reason`
  - 节点资源：`node_memory_Active_bytes`、`node_cpu_seconds_total` 等
- 标签映射：`cluster`, `namespace`, `pod`, `container`, `node`, `app` 等，需与 Kubernetes 对齐。
- 其他扩展：接入自定义 Exporter（存储、网络、GPU）。
- 大规模集群实践：
  - 通过 `kubernetes_sd_config` 自动发现 Service/Pod，避免手工维护 Target；
  - 统一 Label/Annotation 规范（如 `cluster`、`team`、`service`），Prometheus 会自动映射为指标标签；
  - 关键查询可用 Pod UID 或 OwnerReference 作为稳定标识，处理滚动更新带来的名称变化；
  - 搭配 Thanos/Cortex/联邦 Prometheus 横向扩展与远程存储，支撑几十万 Pod 的指标量级。

### 3.3 告警系统
- Alertmanager Webhook / 其他告警通道（PagerDuty、Feishu、钉钉）。
- 告警信息结构：`alertname`、`severity`、`labels`（包含 Pod、Namespace、Node 等）、`annotations`。
- 平台处理流程：
  1. 接收告警 → 解析关联对象；
  2. 拉取 Kubernetes 当前状态 + 近期事件；
  3. 查询 Prometheus 对应时间段指标；
  4. 根据规则引擎评估可能原因与建议操作。

### 3.4 Pod 日志获取策略（混合模式）

#### 3.4.1 两种日志获取方式对比

**方式一：Kubernetes API Server 直接获取（实时日志）**
- **接口**：`GET /api/v1/namespaces/{namespace}/pods/{name}/log`
- **优点**：
  - ✅ **实时性高**：直接从容器运行时获取，无延迟
  - ✅ **无需额外依赖**：不依赖日志系统，即使日志系统故障也能获取
  - ✅ **简单直接**：适合快速诊断当前运行中的 Pod
- **缺点**：
  - ❌ 只能获取**当前运行** Pod 的日志
  - ❌ 无法获取**已删除/已重启** Pod 的历史日志
  - ❌ 功能有限：不支持复杂查询、关键字搜索、聚合统计
  - ❌ 多容器 Pod 需要分别获取每个容器的日志

**方式二：集中式日志系统（历史日志）**
- **接口**：Elasticsearch (`POST /_search`) / Loki (`GET /loki/api/v1/query_range`)
- **优点**：
  - ✅ 可以获取**历史日志**（包括已删除 Pod）
  - ✅ 支持**复杂查询**：关键字搜索、正则匹配、时间范围、聚合统计
  - ✅ 支持**多 Pod 联合查询**：按标签、命名空间批量查询
  - ✅ 支持**日志高亮、分页、统计**等功能
- **缺点**：
  - ❌ 可能有**延迟**：采集 Agent → 传输 → 索引需要时间（通常几秒到几分钟）
  - ❌ 依赖日志系统：如果日志系统故障或未配置，无法获取日志
  - ❌ 需要额外的存储和计算资源

#### 3.4.2 混合策略（推荐）

**诊断时的日志获取策略**：
1. **优先从 K8s API Server 获取实时日志**（如果 Pod 正在运行）
   - 适用于：快速诊断当前问题、需要最新日志、日志系统延迟较高
   - 实现：调用 `GET /api/v1/namespaces/{namespace}/pods/{name}/log?tailLines=100`
2. **回退到日志系统**（如果 K8s API 失败或需要历史数据）
   - 适用于：Pod 已重启/删除、需要查看历史日志、需要复杂查询
   - 实现：调用 Elasticsearch/Loki API 查询历史日志

**具体判断逻辑**：
```
IF Pod 状态 == Running:
    尝试从 K8s API Server 获取实时日志
    IF 成功:
        返回实时日志
    ELSE:
        回退到日志系统
ELSE IF Pod 状态 == CrashLoopBackOff / Error / Terminated:
    直接从日志系统获取历史日志（因为 Pod 可能已重启，K8s API 只能看到当前实例）
ELSE:
    仅从日志系统获取（Pod 已删除或不存在）
```

#### 3.4.3 日志采集架构（日志系统）

1. **节点级采集 Agent**：在每个 K8s 节点运行日志采集 Agent（Fluent Bit/Fluentd/Filebeat/Vector）。
2. **日志收集**：Agent 从容器运行时（containerd/docker）读取容器的 stdout/stderr 日志文件（通常位于 `/var/log/pods/` 或 `/var/lib/docker/containers/`）。
3. **元数据注入**：采集器自动注入 `namespace`、`pod`、`container`、`node`、`labels`、`annotations` 等 Kubernetes 元数据字段。
4. **集中存储**：日志被发送到集中式日志系统（Elasticsearch/Loki）进行存储和索引。

#### 3.4.4 使用场景

- **实时诊断**：Pod 正在运行且需要最新日志 → 优先使用 K8s API
- **历史分析**：Pod 已重启，需要查看重启前的日志 → 使用日志系统
- **批量查询**：需要查询多个 Pod 或按标签筛选 → 使用日志系统
- **复杂分析**：需要关键字搜索、统计、聚合 → 使用日志系统

#### 3.4.5 实现细节

**已实现混合策略**（通过 `DiagnosisDataCollector.collect_logs()` 统一封装）：

1. **Pod 状态检查**：
   - 首先通过 `KubernetesResourceSyncService.fetch_resource_detail()` 获取 Pod 的当前状态
   - 检查 Pod 的 `phase` 字段，判断 Pod 是否处于 `Running` 状态

2. **K8s API 日志获取**（`app/services/resource_sync_service.py` 的 `fetch_pod_logs` 方法）：
   - 使用 `httpx` 调用 `GET /api/v1/namespaces/{namespace}/pods/{name}/log`
   - 支持参数：
     - `tailLines`：获取最后 N 行日志（默认 100）
     - `container`：指定容器名称（多容器 Pod 需要）
     - `sinceSeconds`：获取最近 N 秒的日志（默认 900 秒，即 15 分钟）
   - 自动处理认证（Bearer Token / Basic Auth）
   - 将返回的文本日志转换为结构化格式（包含 timestamp、message、source 字段）

3. **日志系统查询**（`app/services/log_query_service.py`）：
   - Elasticsearch：使用 DSL 查询语法，支持复杂过滤和聚合
   - Loki：使用 LogQL 查询语法，支持流选择器和过滤表达式
   - 查询时使用 Pod 名称、命名空间、时间范围等作为过滤条件
   - 查询结果支持分页、高亮、统计等功能

4. **回退机制**：
   - 如果 Pod 正在运行但 K8s API 获取失败，自动回退到日志系统
   - 如果 Pod 不在运行状态（CrashLoopBackOff、Error、Terminated 等），直接使用日志系统
   - 如果日志系统也未配置，返回错误信息

5. **返回格式统一**：
   - 两种方式返回的日志都统一为相同的结构：
     ```json
     {
       "source": "k8s_api" | "log_system",
       "logs": [
         {
           "timestamp": "2024-01-01T00:00:00Z",
           "message": "log content",
           "source": "k8s_api" | "log_system"
         }
       ],
       "total": 100,
       "error": null
     }
     ```

## 4. 核心功能模块
### 4.1 资源同步模块
- 负责从 Kubernetes 周期性拉取资源，维护本地缓存/数据库。
- 支持多集群：每个集群配置独立的 API 访问凭证与标签。
- 提供查询接口给分析模块（如按命名空间查 Pod、按标签筛选）。

### 4.2 指标查询模块
- 封装 Prometheus HTTP 调用，支持即时查询（`query`）与区间查询（`query_range`）。
- 内置常用指标模板，例如：
  - `pod_cpu_usage(namespace, pod, range)` → 返回最近 range 的 CPU 使用率时序。
  - `pod_restart_rate(namespace, pod, range)` → Pod 重启速率。
- 支持缓存与限流，避免频繁请求导致 Prometheus 压力过大。

### 4.3 告警处理模块
- 监听告警事件，执行以下步骤：
  1. 解析告警标签 → 找到目标对象（Pod / Node / Deployment）。
  2. 查询资源同步模块获取最新状态、关联资源。
  3. 调用指标查询模块拉取关键指标。
  4. 触发规则引擎（如简单阈值、模式匹配）判断可能原因。
  5. 生成诊断报告（JSON / Markdown），供运维系统展示或通知。

### 4.4 规则与诊断模块
- 规则类型：
  - 静态阈值（CPU > 90% 持续 5 分钟）。
  - 状态模式（Pod `CrashLoopBackOff` 且重启次数突增）。
  - 组合条件（节点磁盘空间不足 + Pod 调度失败）。
- 支持自定义插件式扩展，方便根据业务特性添加检测逻辑。

### 4.5 接口与自动化
- 提供 RESTful / gRPC API，支持外部系统（如工单、机器人）调用。
- 可选命令行工具：运维输入 `cluster=prod namespace=foo pod=bar` → 输出分析结果。
- 支持 Webhook 回调或消息推送，把诊断结论回传到告警渠道。

### 4.6 接入配置管理（前端/后端协同）
- **配置项**：
  - Kubernetes API Server 地址、认证方式（kubeconfig 上传、Bearer Token、证书）；
  - Prometheus 接入地址，支持 Basic Auth / Token / mTLS；
  - 日志系统（ELK / Loki 等）HTTP Endpoint 及认证信息；
  - 集群名称、环境标识、默认命名空间范围等元数据。
- **安全与存储**：
  - 前端仅收集必要信息，敏感凭证通过 HTTPS 传输；
  - 后端对 Token/证书做加密存储或接入专用密钥管理系统；
  - 按 RBAC 最小权限原则提示用户准备只读账号。
- **联通性测试**：
  - 前端提供“测试”按钮，调用后端测试接口；
  - 后端依次验证 API Server (`/version` 或 `GET /api/v1/namespaces`)、Prometheus (`/api/v1/status/runtimeinfo` 或测试 Query)、日志系统（`/_cluster/health`、`/ready` 等）；
  - 返回测试结果、错误原因（如认证失败、证书不信任、网络超时），前端直观展示。
- **数据库设计**：
  - 配置表记录地址、认证方式、凭证指纹、启用状态、最后一次健康检查时间与结果；
  - 支持多集群接入，每条记录可绑定集群 ID；
  - 提供启用/禁用、编辑、删除能力，失败的配置提示重新验证。
- **运维可视化**：
  - 列表页展示各集群配置与最近联通状态；
  - 提示证书即将过期或长时间未成功连接的配置；
  - 允许导出配置（不含敏感信息）供审计。

### 4.7 资源同步模块详细设计
- **输入**：集群配置（API 地址、认证信息）、资源拉取范围（命名空间、资源类型）、同步周期。
- **处理流程**：
  1. 根据同步计划调度任务，优先使用 watch，回退到全量 list；
  2. 将返回的资源对象标准化（补充集群 ID、业务标签、OwnerReference 信息）；
  3. 写入缓存与持久化（如 PostgreSQL / MongoDB），记录 resourceVersion；
  4. 通过消息队列（可选）向其他模块发布变更事件。
- **输出**：标准化后的资源实体、变更事件、同步元数据（时间、版本、状态）。
- **接口**：
  - `GET /api/clusters/{id}/resources?kind=Pod&namespace=...`
  - `GET /api/clusters/{id}/resources/{uid}` 返回单个资源详情。
- **异常处理**：连续失败时告警；resourceVersion 过期时自动执行全量重拉；认证失效时标记配置状态为异常。

### 4.8 指标查询模块详细设计
- **输入**：Prometheus 连接信息、查询模板 ID 或自定义 promql、时间范围、聚合粒度。
- **处理流程**：
  1. 验证 promql 与参数合法性（阻止危险查询）；
  2. 根据集群默认模板（CPU/内存/重启）或自定义 promql 生成查询；
  3. 调用 Prometheus `/query` 或 `/query_range`，必要时开启分段查询避免大时间跨度；
  4. 将结果转换为统一的时序结构（timestamp, value, metric labels），供前端或分析模块使用；
  5. 根据策略缓存结果，缓存键包含 promql+时间范围+目标对象。
- **输出**：时序数据、聚合统计（均值、最大值、趋势）、查询元信息（耗时、命中缓存与否）。
- **接口**：
  - `POST /api/metrics/query`（入参：clusterId、templateId 或 promql、start/end/step）；
  - `POST /api/metrics/batch` 支持一次查询多个指标。
- **异常处理**：Prometheus 超时、认证失败、查询语法错误时返回结构化错误码，便于前端提示；记录审计日志。

### 4.9 告警处理模块详细设计
- **输入**：Alertmanager Webhook payload、第三方告警事件、手动触发诊断请求。
- **处理流程**：
  1. 解析告警标签（cluster、namespace、pod、node、severity 等）；
  2. 调用资源同步模块获取最新资源状态与关联对象；
  3. 调用指标查询模块拉取关键指标（CPU、内存、重启、网络）；
  4. 触发诊断规则与知识库/模型流程（见第 9、10 章节）；
  5. 生成诊断结果（结论、证据、建议），写入数据库并推送给通知渠道。
- **输出**：诊断报告、执行日志、告警处理状态（进行中、已完成、需要人工介入）。
- **接口**：
  - `POST /api/alerts/webhook` 接收 Alertmanager 推送；
  - `POST /api/diagnosis/run`（入参：clusterId、namespace、pod、告警上下文）。
- **异常处理**：如果某一步失败（指标查询超时、知识库无结果），记录失败原因并按照模型/搜索兜底策略继续执行；必要时通知人工。

## 5. 诊断流程详细设计

### 5.0 统一诊断流程（核心思想）

**核心思想**：统一流程，差异化数据收集

不管诊断什么资源类型（Pod、Node、Deployment、Service 等），都用**同一套诊断流程**，只是收集的数据不同。

**统一流程**：
```
触发诊断
  ↓
1. 收集数据（统一入口）
   ├─→ 从 API Server 获取资源状态和配置
   ├─→ 从监控系统获取指标数据
   └─→ 从日志系统获取日志数据
  ↓
2. 规则检测（统一规则引擎）
   └─→ 检测已知问题模式
  ↓
3. AI 分析（统一 LLM 推理）⭐【核心改进】
   └─→ 基于实际数据，直接分析问题，给出置信分
   └─→ 如果置信分 >= 0.8，直接完成诊断
   └─→ 如果置信分 < 0.8，继续执行后续步骤
  ↓
4. 知识库搜索（统一搜索，条件触发）
   └─→ 如果AI分析置信分 < 0.8，查找历史案例
  ↓
5. 扩展K8s信息收集（条件触发）
   └─→ 如果知识库没有高置信度结果，收集更多资源信息
  ↓
6. 外部搜索（可选，条件触发）
   └─→ 如果AI和知识库都不确定，联网搜索
  ↓
7. 生成结论
   ├─→ 根因分析
   ├─→ 解决方案
   └─→ 置信度
  ↓
8. 判断是否需要继续
   ├─→ 如果置信分 >= 0.8 → 完成
   └─→ 如果经过8个步骤后置信分 < 0.8 → 申请人工介入
```

**差异化数据收集**：
- **Pod**：收集 Pod 状态、容器指标、容器日志
- **Node**：收集 Node 状态、节点指标、Kubelet 日志
- **Service**：收集 Service 配置、Endpoints、网络指标
- **Deployment**：收集 Deployment 状态、副本状态、Pod 列表

### 5.1 诊断流程总览（详细版）

```
┌─────────────────────────────────────────────────────────────────┐
│                    K8s 运维诊断完整流程                           │
└─────────────────────────────────────────────────────────────────┘

[触发诊断]
    │
    ├─→ 1. 创建诊断记录 (diagnosis_records)
    │      - 状态: running
    │      - 记录: 集群、资源、触发来源
    │
    ├─→ 2. 执行第一轮迭代 (_execute_iteration)
    │      │
    │      ├─→ 2.1 初始化迭代
    │      │      - 获取历史记忆摘要
    │      │      - 构建推理 Prompt
    │      │      - 创建迭代记录 (diagnosis_iterations)
    │      │      - 保存初始症状到记忆
    │      │
    │      ├─→ 2.2 执行动作计划 (_run_single_iteration)
    │      │      │
    │      │      ├─→ 动作1: 收集指标 (collect_metrics)
    │      │      │      - 查询 Prometheus
    │      │      │      - 指标: CPU/内存/重启率
    │      │      │      - 保存到记忆 (memory_type: metric)
    │      │      │
    │      │      ├─→ 动作2: 收集日志 (collect_logs) [混合策略]
    │      │      │      - 优先: K8s API Server (实时日志)
    │      │      │      - 回退: 日志系统 (ELK/Loki)
    │      │      │      - 保存到记忆 (memory_type: log)
    │      │      │
    │      │      ├─→ 动作3: 规则引擎评估 (rule_evaluate)
    │      │      │      - 评估: CPU/内存/重启率阈值
    │      │      │      - 检测: 日志错误模式
    │      │      │      - 保存到记忆 (memory_type: rule)
    │      │      │
    │      │      ├─→ 第一步: 基于实际数据的模型分析 (llm_analysis_with_data) ⭐【核心改进】
    │      │      │      - **关键改进**：收集数据后，立即让模型分析实际数据，判断问题，给出置信分
    │      │      │      - 调用 `DiagnosisLlmService.call_llm()`
    │      │      │      - 传入收集的基础数据（指标、日志、规则检测结果、API数据、变更事件）
    │      │      │      - 构建结构化 Prompt (5 Why/证据链)，**强调日志优先原则**
    │      │      │      - 模型直接分析：问题是什么？根因是什么？置信度多少？
    │      │      │      - **重要**：如果日志中有明确的错误信息（如 UnknownHostException、Connection refused），
    │      │      │                模型必须直接使用这些错误作为根因，而不是推测配置问题
    │      │      │      - 调用 LLM (Ollama)，解析 JSON 输出
    │      │      │      - 提取置信度（confidence）
    │      │      │      - 保存到记忆 (memory_type: llm)
    │      │      │      - **如果置信分 >= 0.8，直接完成诊断，跳过后续步骤（知识库搜索等）**
    │      │      │      - **如果置信分 < 0.8，继续执行后续步骤（搜索知识库、扩展信息等）**
    │      │      │
    │      │      ├─→ 第二步: 生成问题描述（用于知识库搜索） (generate_problem_description) [条件触发]
    │      │      │      - **触发条件**：第一步的模型分析置信分 < 0.8
    │      │      │      - **跳过条件**：如果第一步置信分 >= 0.8，跳过此步骤
    │      │      │      - 基于收集到的数据（指标、日志、规则检测结果、API数据、第一步的模型分析结果）
    │      │      │      - 调用 LLM 生成清晰、简洁的问题总结，用于知识库搜索
    │      │      │      - 问题总结包含：问题类型、关键症状、资源信息、具体错误信息
    │      │      │
    │      │      ├─→ 第三步: 搜索知识库 (search_knowledge) [条件触发]
    │      │      │      - **触发条件**：第一步的模型分析置信分 < 0.8
    │      │      │      - **跳过条件**：如果第一步置信分 >= 0.8，跳过此步骤
    │      │      │      - 基于第二步生成的问题描述搜索
    │      │      │      - 查询 OpenSearch（向量搜索 + 关键词搜索）
    │      │      │      - 返回相关历史案例文档（包含完整内容）
    │      │      │      - 保存到记忆 (memory_type: knowledge)
    │      │      │
    │      │      ├─→ 第四步: 评估知识库内容准确性 (evaluate_knowledge) [条件触发]
    │      │      │      - **触发条件**：第三步搜索知识库后找到结果
    │      │      │      - **跳过条件**：如果第三步未搜索到结果，跳过此步骤
    │      │      │      - 如果知识库搜索到结果，用 LLM 评估问题和答案的准确度
    │      │      │      - 对每个知识库文档进行评估，生成置信分（0.0-1.0）
    │      │      │      - 取最高置信分作为知识库置信分
    │      │      │      - 筛选出相关的文档（is_relevant=True 且置信分>0）
    │      │      │      - 保存评估结果到记忆
    │      │      │      - **如果知识库置信分 >= 0.8，直接完成诊断，跳过后续步骤**
    │      │      │
    │      │      ├─→ 第五步: 扩展 K8s 信息收集（第一层扩展） (expand_k8s_resources) [条件触发]
    │      │      │      - **触发条件**：
    │      │      │        - 第一步的模型分析置信分 < 0.8 **AND**
    │      │      │        - (第三步未搜索到知识库 **OR** 第四步知识库置信分 < 0.8)
    │      │      │      - **跳过条件**：
    │      │      │        - 如果第一步置信分 >= 0.8，跳过此步骤
    │      │      │        - 如果第四步知识库置信分 >= 0.8，跳过此步骤
    │      │      │      - 收集相关 K8s 资源信息（更大范围的信息获取）
    │      │      │        ├─→ Deployment/StatefulSet/DaemonSet (Pod 控制器)
    │      │      │        ├─→ Service (服务发现)
    │      │      │        ├─→ ConfigMap/Secret (配置)
    │      │      │        ├─→ Node (节点状态)
    │      │      │        ├─→ ResourceQuota (资源配额)
    │      │      │        ├─→ NetworkPolicy (网络策略)
    │      │      │        └─→ PVC (持久化存储)
    │      │      │      - 保存到记忆 (memory_type: k8s_resource)
    │      │      │
    │      │      ├─→ 第六步: 基于扩展 K8s 信息的模型分析 (llm_analysis_with_k8s_resources) [条件触发]
    │      │      │      - **触发条件**：已完成第五步扩展K8s信息收集
    │      │      │      - **跳过条件**：
    │      │      │        - 如果第一步置信分 >= 0.8，跳过此步骤
    │      │      │        - 如果第四步知识库置信分 >= 0.8，跳过此步骤
    │      │      │      - 基于扩展收集的 K8s 资源信息，重新调用 LLM 分析
    │      │      │      - 构建结构化 Prompt (5 Why/证据链)，**强调日志优先原则**
    │      │      │      - 传入收集的基础数据（指标、日志、规则检测结果、API数据）、扩展的 K8s 资源信息
    │      │      │      - **不传入知识库内容**（因为知识库置信分<0.8，已不可信）
    │      │      │      - 调用 LLM (Ollama)，解析 JSON 输出
    │      │      │      - 提取置信度（confidence）
    │      │      │      - 保存到记忆 (memory_type: llm)
    │      │      │      - **如果置信分 >= 0.8，完成诊断，跳过后续步骤**
    │      │      │
    │      │      ├─→ 第七步: 外部搜索 (search_external) [条件触发]
    │      │      │      - **触发条件**：
    │      │      │        - 第一步的模型分析置信分 < 0.8 **AND**
    │      │      │        - (第四步未执行或知识库置信分 < 0.8) **AND**
    │      │      │        - (第六步未执行或第六步置信分 < 0.8)
    │      │      │      - **跳过条件**：
    │      │      │        - 如果第一步置信分 >= 0.8，跳过此步骤
    │      │      │        - 如果第四步知识库置信分 >= 0.8，跳过此步骤
    │      │      │        - 如果第六步置信分 >= 0.8，跳过此步骤
    │      │      │      - 进行外部搜索（Searxng）
    │      │      │      - 使用第二步生成的问题总结作为搜索关键词
    │      │      │      - 查询 Searxng API，获取外部参考信息
    │      │      │      - 保存到记忆 (memory_type: search)
    │      │      │
    │      │      └─→ 第八步: 基于外部搜索结果的模型分析 (llm_final_with_external) [条件触发]
    │      │              - **触发条件**：第七步进行了外部搜索
    │      │              - **跳过条件**：如果第七步未执行，跳过此步骤
    │      │              - 如果获得了外部搜索结果，使用外部搜索结果重新调用 LLM
    │      │              - 传入收集的基础数据（指标、日志、规则检测结果、API数据）、扩展的 K8s 资源信息、外部搜索结果
    │      │              - **不传入知识库内容**（因为知识库置信分<0.8，已不可信）
    │      │              - 调用 LLM，解析 JSON 输出
    │      │              - 提取置信度（confidence）
    │      │              - 保存到记忆 (memory_type: llm)
    │      │              - **如果经过这8个步骤后，置信分仍然 < 0.8，则生成诊断报告，申请人工介入**
    │      │
    │      ├─→ 2.3 生成诊断摘要 (_generate_summary_enhanced)
    │      │      - 从结构化 LLM 输出提取信息
    │      │      - 或基于规则生成基础解决方案
    │      │      - 计算置信度
    │      │
    │      ├─→ 2.4 完成迭代记录
    │      │      - 保存推理输出、动作计划、动作结果
    │      │      - 保存根因分析、证据链
    │      │
    │      ├─→ 2.5 应用迭代结果 (_apply_iteration_result)
    │      │      - 更新诊断记录: metrics/logs/recommendations
    │      │      - 保存结构化解决方案
    │      │      - 保存根因/时间线/影响范围到 symptoms
    │      │
    ├─→ 3. 判断终止条件（基于最终的置信分）
    │      │
    │      ├─→ 条件1: 经过这8个步骤后，置信分 >= 阈值 (0.8)
    │      │      - 置信分来源优先级（按执行顺序，取第一个 >= 0.8 的置信分）：
    │      │        1. **基于实际数据的模型分析置信分（第一步）** ⭐【最高优先级】
    │      │           - 如果日志中有明确的错误信息，模型应该能够直接识别并给出高置信分
    │      │           - 这是最直接、最可靠的证据，优先使用
    │      │        2. 知识库评估置信分（第四步，如果知识库命中且置信分 >= 0.8）
    │      │        3. 扩展K8s信息的模型分析置信分（第六步，如果基于扩展资源分析后置信分 >= 0.8）
    │      │        4. 外部搜索后的模型分析置信分（第八步，如果基于外部搜索结果分析后置信分 >= 0.8）
    │      │      - 状态: completed
    │      │      - 返回前端，展示诊断结果
    │      │      - 知识沉淀：自动保存到知识库
    │      │
    │      ├─→ 条件2: 经过这8个步骤后，置信分 < 阈值 (0.8)
    │      │      - 状态: pending_human
    │      │      - **生成诊断报告**（包含收集的所有数据、分析过程、当前置信分、8个步骤的执行结果）
    │      │      - **申请人工介入**，提供人工诊断入口
    │      │      - 说明：单轮迭代内已完成所有8个诊断步骤（模型分析、知识库搜索、扩展K8s信息、外部搜索等），
    │      │              但置信分仍不足，需要人工专家介入进行深度分析
    │      │      - 注意：不再进行下一轮迭代，因为单轮迭代内已尝试所有可能的诊断方法
    │      │
    │      └─→ 条件4: 发生错误
    │              - 状态: failed
    │              - 记录错误信息，建议人工介入
    │
    └─→ 4. 返回诊断结果
            - 包含: 诊断记录、迭代历史、上下文记忆
```

### 5.2 核心方法调用链

```python
# 手动触发
POST /api/v1/observability/diagnosis/run
  → DiagnosisService.trigger_diagnosis()
    → _execute_iteration()
      → _run_single_iteration()
        → data_collector.collect_data()  # 统一入口，内部包含 collect_metrics / collect_logs
        → rule_service.evaluate()  # 规则引擎评估
        → llm_service.call_llm()  # ⭐第一步：基于实际数据的模型分析（核心改进）
          → _build_structured_llm_prompt()  # 传入基础数据（指标、日志、规则、API数据、变更事件）
          → _parse_llm_structured_output()  # 解析JSON输出，提取置信分
          → 如果置信分 >= 0.8: 直接完成诊断，跳过后续步骤
        → llm_service.generate_problem_summary() [条件触发：如果第一步置信分<0.8]  # 第二步：生成问题描述（用于知识库搜索）
        → data_collector.search_knowledge(problem_description) [条件触发：如果第一步置信分<0.8]  # 第三步：搜索知识库
        → llm_service.evaluate_knowledge_relevance() [条件触发：如果搜索到结果]  # 第四步：评估知识库准确性并生成置信分
        → k8s_collector.collect_related_k8s_resources() [条件触发：如果第一步置信分<0.8且知识库未命中或置信分<0.8]  # 第五步：扩展K8s信息收集
        → llm_service.call_llm() [条件触发：如果第五步执行]  # 第六步：基于扩展K8s信息的模型分析
          → _build_structured_llm_prompt()  # 传入基础数据和扩展的K8s资源信息，不传知识库内容
          → _parse_llm_structured_output()
        → data_collector.search_external() [条件触发：如果前面步骤置信分都<0.8]  # 第七步：外部搜索
        → llm_service.call_llm() [条件触发：如果进行了外部搜索]  # 第八步：基于外部搜索结果的模型分析
          → _build_structured_llm_prompt()  # 传入基础数据、扩展K8s资源和外部搜索结果，不传知识库内容
          → _parse_llm_structured_output()
        → _generate_summary_enhanced()  # 生成诊断摘要（使用最终的置信分）
        → _apply_iteration_result()  # 应用迭代结果
      → 判断终止条件（基于最终置信分）
        → 如果置信分 >= 0.8: completed（返回前端）
        → 如果经过这8个步骤后，置信分 < 0.8: pending_human（生成报告，申请人工介入）
      → 不再进行下一轮迭代（单轮迭代内已完成所有诊断步骤）

# 告警触发
POST /api/v1/observability/alerts/webhook
  → DiagnosisService.trigger_diagnosis()

# 注意：不再进行多轮迭代
# 单轮迭代内已完成所有8个诊断步骤，如果置信分仍<0.8，直接申请人工介入
# 以下内容已废弃，保留用于历史参考：
# Celery Task: continue_diagnosis (已废弃)
#   → DiagnosisService.continue_diagnosis() (已废弃)
#     → _execute_iteration() (已废弃)
#       → ... (同上)
```

### 5.3 详细流程步骤

#### 5.3.1 诊断触发阶段

**入口点**：
- `POST /api/v1/observability/diagnosis/run` - 手动触发
- `POST /api/v1/observability/alerts/webhook` - 告警触发
- 注意：不再使用多轮迭代，单轮迭代内完成所有8个诊断步骤

**输入参数**：
```python
{
    "cluster_id": int,           # 集群ID
    "namespace": str,            # 命名空间
    "resource_type": str,        # 资源类型（pods/deployments等）
    "resource_name": str,        # 资源名称
    "trigger_source": str,       # 触发来源：manual/alert/schedule
    "trigger_payload": dict      # 触发上下文（告警信息等）
}
```

**处理步骤**：
1. 验证集群配置是否存在
2. 构建运行时配置（解密凭证）
3. 创建诊断记录（`diagnosis_records` 表）
   - 初始状态：`status = "running"`
   - 记录症状、触发来源、上下文信息
   - 创建初始事件："诊断开始"

**代码位置**：`diagnosis_service.py::trigger_diagnosis()`

#### 5.3.2 单轮迭代执行阶段

**核心方法**：`_execute_iteration()`

**初始化迭代**：
1. 获取历史记忆摘要（查询最近 N 条记忆）
2. 构建推理 Prompt（包含当前症状、历史事实、未解决假设）
3. 创建迭代记录（`diagnosis_iterations` 表）
4. 保存初始症状（如果是第一轮迭代）

**执行动作计划**（按顺序执行）：

1. **collect_metrics** - 收集指标
   - 调用 `PrometheusMetricsService` 查询指标
   - 使用模板查询：`pod_cpu_usage`, `pod_memory_usage`, `pod_restart_rate`
   - 时间范围：最近 30 分钟（可配置，默认2小时）
   - 保存结果到记忆（`memory_type = "metric"`）

2. **collect_logs** - 收集日志（混合策略）
   - 检查 Pod 状态
   - 如果 Pod 正在运行：优先从 K8s API Server 获取实时日志
   - 回退到日志系统（如果 K8s API 失败或 Pod 不在运行）
   - 时间范围：最近 15 分钟（可配置，默认2小时）
   - 保存结果到记忆（`memory_type = "log"`）

3. **rule_evaluate** - 规则引擎评估
   - CPU 使用率过高：`CPU_THRESHOLD = 0.8` (80%)
   - 内存使用过高：`MEMORY_THRESHOLD_BYTES = 1.5GB`
   - 重启频率过高：`RESTART_THRESHOLD = 1.0` (每5分钟)
   - 日志错误模式：检测 ERROR/FATAL 关键字
   - 保存到记忆（`memory_type = "rule"`）

4. **llm_analysis_with_data** - 基于实际数据的模型分析（第一步）⭐【核心改进】
   - **关键改进**：收集数据后，立即让模型分析实际数据，判断问题，给出置信分
   - **触发条件**：无（总是执行，这是第一步）
   - 调用 `DiagnosisLlmService.call_llm()`
   - 传入收集的基础数据：
     - 指标数据（CPU、内存、重启率等）
     - 日志数据（优先包含 ERROR/WARNING 日志）
     - 规则检测结果（CPU阈值、内存阈值等）
     - API数据（Pod状态、配置等）
     - 变更事件（最近24小时的配置变更）
   - 构建结构化 Prompt（5 Why/证据链），**强调日志优先原则**：
     - 必须优先分析日志中的错误信息，这是诊断问题的直接证据
     - 如果日志中有明确的错误（如 UnknownHostException、Connection refused、Timeout 等），
       必须直接使用这些错误信息作为根因，而不是推测配置问题
     - 避免在没有证据的情况下推测配置问题
   - 模型直接分析：问题是什么？根因是什么？置信度多少？
   - 调用 LLM (Ollama)，解析 JSON 输出
   - 提取置信度（`confidence`）
   - 保存到记忆（`memory_type = "llm"`）
   - **如果置信分 >= 0.8，直接完成诊断，跳过后续步骤（知识库搜索等）**
   - **如果置信分 < 0.8，继续执行后续步骤（搜索知识库、扩展信息等）**

5. **generate_problem_description** - 生成问题描述（第二步，条件触发）
   - **触发条件**：第一步的模型分析置信分 < 0.8
   - **跳过条件**：如果第一步置信分 >= 0.8，跳过此步骤
   - 调用 `DiagnosisLlmService.generate_problem_summary()`
   - 基于收集到的数据（指标、日志、规则检测结果、API数据、变更事件、第一步的模型分析结果）
   - LLM 生成清晰、简洁的问题总结，用于知识库搜索
   - 问题总结包含：
     - 问题类型（如：Pod 启动失败、CPU 异常、内存泄漏等）
     - 关键症状（如：重启频繁、资源占用高、日志报错等）
     - 资源信息（Pod/Deployment 名称、命名空间）
     - 具体错误信息（如：UnknownHostException: zk-hs.kaka.svc.cluster.local）
   - 如果没有 LLM，使用简单描述：`"{resource_type} {resource_name} 在命名空间 {namespace} 出现问题"`

6. **search_knowledge** - 搜索知识库（第三步，条件触发）
   - **触发条件**：第一步的模型分析置信分 < 0.8
   - **跳过条件**：如果第一步置信分 >= 0.8，跳过此步骤
   - 基于第二步生成的问题描述搜索
   - 调用 `DiagnosisDataCollector.search_knowledge(problem_description)`
   - 内部调用 `SearchService.mixed_search()`（OpenSearch）
     - 向量搜索 + 关键词搜索
     - 返回 Top-K 相关文档（默认 5 条）
   - 返回完整的文档信息（包含 document_id, title, content, score, metadata）
   - 保存到记忆（`memory_type = "knowledge"`）

7. **evaluate_knowledge** - 评估知识库内容准确性（第四步，条件触发）
   - **触发条件**：第三步搜索知识库后找到结果
   - **跳过条件**：如果第三步未搜索到结果，跳过此步骤
   - 如果知识库搜索到结果，用 LLM 评估问题和答案的准确度
   - 调用 `DiagnosisLlmService.evaluate_knowledge_relevance()` 对每个文档进行评估
   - 返回评估结果：
     - `is_relevant`: 是否相关
     - `confidence`: 置信分（0.0-1.0）
     - `match_reason`: 相关/不相关的原因
   - 取所有文档中的最高置信分作为知识库置信分
   - 筛选出相关的文档（`is_relevant=True 且置信分>0`）
   - 如果没有相关文档，将 `knowledge_refs` 设为 `None`
   - 保存评估结果到记忆
   - **如果知识库置信分 >= 0.8，直接完成诊断，跳过后续步骤**

8. **expand_k8s_resources** - 扩展 K8s 信息收集（第五步，条件触发）
   - **触发条件**：
     - 第一步的模型分析置信分 < 0.8 **AND**
     - (第三步未搜索到知识库 **OR** 第四步知识库置信分 < 0.8)
   - **跳过条件**：
     - 如果第一步置信分 >= 0.8，跳过此步骤
     - 如果第四步知识库置信分 >= 0.8，跳过此步骤
   - 调用 `K8sResourceCollector.collect_related_k8s_resources()`
   - 收集相关 K8s 资源信息（更大范围的信息获取）：
     - Deployment/StatefulSet/DaemonSet（Pod 的控制器）
     - Service（服务发现）
     - ConfigMap/Secret（配置）
     - Node（节点状态）
     - ResourceQuota（资源配额）
     - NetworkPolicy（网络策略）
     - PVC（持久化存储）
   - 保存到记忆（`memory_type = "k8s_resource"`）

9. **llm_analysis_with_k8s_resources** - 基于扩展 K8s 信息的模型分析（第六步，条件触发）
   - **触发条件**：已完成第五步扩展K8s信息收集
   - **跳过条件**：
     - 如果第一步置信分 >= 0.8，跳过此步骤
     - 如果第四步知识库置信分 >= 0.8，跳过此步骤
   - 基于扩展收集的 K8s 资源信息，重新调用 LLM 分析
   - 调用 `DiagnosisLlmService.call_llm()`
   - 构建结构化 Prompt（5 Why/证据链），**强调日志优先原则**
   - 传入：
     - 收集的基础数据（指标、日志、规则检测结果、API数据）
     - 扩展的 K8s 资源信息
   - **不传入知识库内容**（因为知识库置信分<0.8，已不可信）
   - 调用 LLM (Ollama)，解析 JSON 输出
   - 提取置信度（`confidence`）
   - 保存到记忆（`memory_type = "llm"`）
   - **如果置信分 >= 0.8，完成诊断，跳过后续步骤**

10. **search_external** - 外部搜索（第七步，条件触发）
    - **触发条件**：
      - 第一步的模型分析置信分 < 0.8 **AND**
      - (第四步未执行或知识库置信分 < 0.8) **AND**
      - (第六步未执行或第六步置信分 < 0.8)
    - **跳过条件**：
      - 如果第一步置信分 >= 0.8，跳过此步骤
      - 如果第四步知识库置信分 >= 0.8，跳过此步骤
      - 如果第六步置信分 >= 0.8，跳过此步骤
    - 调用 `DiagnosisDataCollector.search_external(resource_name, namespace)`
    - 使用第二步生成的问题总结作为搜索关键词
    - 查询 Searxng API，获取外部参考信息
    - 保存到记忆（`memory_type = "search"`）

11. **llm_final_with_external** - 基于外部搜索结果的模型分析（第八步，条件触发）
    - **触发条件**：第七步进行了外部搜索
    - **跳过条件**：如果第七步未执行，跳过此步骤
    - 如果获得了外部搜索结果，使用外部搜索结果重新调用 LLM
    - 调用 `DiagnosisLlmService.call_llm()`
    - **重要**：不传入知识库内容（因为知识库置信分<0.8，已不可信）
    - 传入：
      - 收集的基础数据（指标、日志、规则检测结果、API数据）
      - 扩展的 K8s 资源信息（保留扩展信息，不减少信息量）
      - 外部搜索结果
    - 调用 LLM，解析 JSON 输出
    - 提取置信度（`confidence`）
    - 保存到记忆（`memory_type = "llm"`）

**完成迭代**：
1. 汇总动作结果
2. 确定最终置信分（按执行顺序，取第一个 >= 0.8 的置信分）：
   - **第一步的模型分析置信分**（最高优先级，如果 >= 0.8）
   - 否则，如果知识库命中且知识库置信分 >= 0.8，使用知识库置信分（第四步）
   - 否则，如果进行了扩展K8s信息收集且模型分析置信分 >= 0.8，使用扩展K8s信息的模型分析置信分（第六步）
   - 否则，如果进行了外部搜索，使用基于外部搜索结果的模型分析置信分（第八步）
   - 否则，使用最后一次模型调用的置信分
3. 解析和结构化 LLM 输出
4. 生成解决方案推荐（立即缓解措施、根本解决方案、预防措施）
5. 完成迭代记录
6. 应用迭代结果到诊断记录

**判断终止条件（基于最终的置信分）**：
- ✅ **经过这8个步骤后，置信分 >= 阈值 (0.8)**：
  - 置信分来源优先级（按执行顺序，取第一个 >= 0.8 的置信分）：
    1. **基于实际数据的模型分析置信分（第一步）** ⭐【最高优先级】
       - 如果日志中有明确的错误信息，模型应该能够直接识别并给出高置信分
       - 这是最直接、最可靠的证据，优先使用
    2. 知识库评估置信分（第四步，如果知识库命中且置信分 >= 0.8）
    3. 扩展K8s信息的模型分析置信分（第六步，如果基于扩展资源分析后置信分 >= 0.8）
    4. 外部搜索后的模型分析置信分（第八步，如果基于外部搜索结果分析后置信分 >= 0.8）
  - 状态：`completed`
  - 返回前端，展示诊断结果
  - 知识沉淀：自动保存到知识库
  
- ⚠️ **经过这8个步骤后，置信分 < 阈值 (0.8)**：
  - 状态：`pending_human`
  - **生成诊断报告**（包含收集的所有数据、分析过程、当前置信分、8个步骤的执行结果）
  - **申请人工介入**，提供人工诊断入口
  - 说明：单轮迭代内已完成所有8个诊断步骤（模型分析、知识库搜索、扩展K8s信息、外部搜索等），
           但置信分仍不足，需要人工专家介入进行深度分析
  - 注意：不再进行下一轮迭代，因为单轮迭代内已尝试所有可能的诊断方法
  
- ❌ **发生错误**：
  - 状态：`failed`
  - 记录错误信息，建议人工介入

#### 5.3.3 迭代终止条件详细说明

**置信分来源（按执行顺序，取第一个 >= 0.8 的置信分）**：
1. **基于实际数据的模型分析置信分（第一步）** ⭐【最高优先级】
   - 收集数据后，立即让模型分析实际数据，判断问题，给出置信分
   - 如果日志中有明确的错误信息，模型应该能够直接识别并给出高置信分
   - 这是最直接、最可靠的证据，优先使用
2. 知识库评估置信分（第四步）：如果知识库搜索到结果，由 LLM 评估每个文档的准确性，取最高置信分
3. 扩展K8s信息的模型分析置信分（第六步）：如果扩展信息后知识库仍无高置信度结果，由模型基于扩展资源分析并生成置信分
4. 外部搜索后的模型分析置信分（第八步）：如果扩展K8s信息后模型分析置信分仍<0.8，基于外部搜索结果由模型分析并生成置信分

**终止条件判断流程**：
1. 获取最终置信分（按执行顺序，取第一个 >= 0.8 的置信分，基于8个步骤的执行结果）
2. 判断置信分是否 >= 0.8：
   - 是 → `completed`（返回前端，展示诊断结果）
   - 否 → `pending_human`（生成报告，申请人工介入）
3. **重要**：单轮迭代内已完成所有8个诊断步骤，不再进行多轮迭代
   - 单轮迭代内已尝试所有可能的诊断方法（模型分析、知识库搜索、扩展K8s信息、外部搜索等）
   - 如果置信分仍不足，说明问题复杂，需要人工专家介入进行深度分析

**单轮迭代内的完整诊断流程**：
- 在单轮迭代内，依次执行8个诊断步骤：
  1. **第一步**：基于实际数据的模型分析 ⭐【核心改进】
     - 收集数据后，立即让模型分析实际数据，判断问题，给出置信分
     - 如果置信分 >= 0.8，直接完成诊断，跳过后续步骤
  2. **第二步**：生成问题描述（用于知识库搜索，条件触发）
  3. **第三步**：搜索知识库（条件触发）
  4. **第四步**：评估知识库内容准确性（条件触发）
  5. **第五步**：扩展K8s信息收集（第一层扩展，条件触发）
  6. **第六步**：基于扩展K8s信息的模型分析（条件触发）
  7. **第七步**：外部搜索（条件触发）
  8. **第八步**：基于外部搜索结果的模型分析（条件触发）

**终止条件**：
- **如果经过这8个步骤后，置信分 >= 0.8**：
  - 状态：`completed`
  - 返回前端，展示诊断结果
  - 知识沉淀：自动保存到知识库
  
- **如果经过这8个步骤后，置信分 < 0.8**：
  - 状态：`pending_human`
  - **生成诊断报告**（包含收集的所有数据、分析过程、当前置信分、8个步骤的执行结果）
  - **申请人工介入**，提供人工诊断入口
  - 说明：单轮迭代内已完成所有8个诊断步骤（模型分析、知识库搜索、扩展K8s信息、外部搜索等），
           但置信分仍不足，需要人工专家介入进行深度分析

#### 5.3.4 迭代终止条件示例

**注意**：以下示例中的"深度诊断"相关内容为原多轮迭代设计的一部分，现已废弃。单轮迭代内已完成所有8个诊断步骤。

**原设计中深度诊断的额外信息**（已废弃，保留用于历史参考）：

1. **K8s Events（集群事件）** ⭐
   - Pod 相关事件：收集与目标 Pod 直接相关的所有事件（最近 20 条）
   - 相关资源事件：收集 Deployment、Node、ReplicaSet 等资源的事件（最近 20 条）
   - 分析价值：通过事件历史了解资源变化过程，找出问题发生的时间点和原因

2. **同一 Deployment/StatefulSet 下的其他 Pod** ⭐
   - 通过 Pod 的 `ownerReferences` 找到控制器
   - 收集同一控制器下的所有 Pod 状态
   - 对比分析：如果其他 Pod 正常 → 特定 Pod 的问题；如果其他 Pod 也异常 → 控制器或配置问题

3. **同一节点上的其他 Pod** ⭐
   - 通过 Pod 的 `spec.nodeName` 找到节点
   - 收集同一节点上的所有 Pod（跨命名空间，最多 20 个）
   - 对比分析：如果节点上其他 Pod 正常 → 不是节点级别问题；如果节点上多个 Pod 异常 → 节点级别问题

4. **命名空间级别的统计信息**
   - 统计命名空间下的 Pod 总数
   - 统计各状态的 Pod 数量（Running、Pending、CrashLoopBackOff、Error 等）
   - 分析价值：判断是否是命名空间级别的问题（ResourceQuota、NetworkPolicy 等）

5. **更长时间范围的指标和日志** ⭐
   - 扩展指标时间范围到 2-4 小时
   - 扩展日志时间范围到 2-4 小时
   - 分析问题发生前后的趋势变化

6. **历史对比分析** ⭐
   - 配置变化对比：对比问题发生前后的配置变化（Pod、Deployment、ConfigMap 等）
   - 指标数据对比：对比历史同期（如昨天同一时间）的指标数据
   - 资源状态对比：对比 Pod 状态变化时间线

**说明**：原设计中，这些信息会在下一轮迭代中收集，现已改为在单轮迭代的8个步骤内完成所有诊断方法。

#### 5.3.5 生成诊断报告（无法判断时）

**触发条件**：
- **经过这8个步骤后，置信分 < 0.8**（主要触发条件）
- 或置信度持续低于阈值且已收集所有可用信息

**报告内容**：
1. 问题摘要
2. 已收集的信息清单
3. 分析结果（已排除的可能原因、可疑但无法确认的问题点）
4. 建议的人工排查方向
5. 下一步操作建议

**保存方式**：保存到诊断记录的 `recommendations` 字段，状态设置为 `pending_human`

#### 5.3.6 多轮迭代调度阶段（已废弃）

**注意**：根据优化后的流程，单轮迭代内已完成所有8个诊断步骤，不再进行多轮迭代。

**原设计说明**：
- 原设计中，如果置信分<0.8且未达到最大迭代次数，会调度下一轮迭代进行深度诊断
- 优化后：单轮迭代内已尝试所有可能的诊断方法（模型分析、知识库搜索、扩展K8s信息、外部搜索等）
- 如果经过8个步骤后，置信分仍<0.8，直接申请人工介入，不再进行多轮迭代

**保留原因**：
- 此章节保留用于历史参考，实际实现中不再使用多轮迭代逻辑
- 相关配置项（如`MAX_ITERATIONS`）保留但不再使用

#### 5.3.7 人机协同阶段

**触发条件**：
- **经过这8个步骤后，置信分 < 0.8**（主要触发条件）
- LLM 推理建议需要人工介入
- 动作执行失败需要人工处理

**状态**：`status = "pending_human"`

**处理流程**：
1. 诊断记录状态更新为 `pending_human`
2. **生成诊断报告**（包含收集的所有数据、分析过程、当前置信分、8个步骤的执行结果）
3. **申请人工介入**，提供人工诊断入口
4. 等待运维人员反馈
5. 运维人员通过 API 提交反馈：`POST /api/v1/observability/diagnosis/{id}/feedback`
   - **反馈类型（feedback_type）**：前端以下拉菜单提供固定选项  
     - `confirmed`（已确认根因，诊断结论正确）  
     - `continue_investigation`（继续排查，当前结论不可信，需要更多数据）  
     - `custom`（其他情况，需补充说明）  
   - 若选择 `custom`，需要填写 `feedback_notes`；若选择 `confirmed`，可选填写已采取动作。
6. 反馈写入记忆（`memory_type = "human_feedback"`），并记录 `feedback_type`、`notes`、`iteration_no`
7. 说明：单轮迭代内已完成所有8个诊断步骤，但置信分仍不足，需要人工专家介入进行深度分析；如果人工确认结论，将进入知识沉淀；如果需要继续排查，将触发新的诊断迭代（见 5.3.8）

#### 5.3.8 反馈驱动的二次诊断（继续排查）

运维人员选择“继续排查”后，需要系统自动收集更多信息并执行后续步骤，避免仅依据早期高置信度就结束诊断。

**核心逻辑**：
1. 记录本次反馈关联的迭代号与已执行的最高步骤（例如在第2步达到置信分 0.8）；
2. 将 `llm_confidence_step1` 强制写入 0.5，并生成事件 `用户反馈：继续排查`；
3. 创建新的迭代 `iteration_{n+1}`，并在该迭代设置 `min_steps_before_exit = 3`，确保至少执行到第3步（即使中途置信分再次 ≥0.8 也不会提前结束）；
4. 新迭代会重新执行第1步到第3步（模型分析→生成问题描述→搜索知识库）；若此时置信分仍不足，则继续执行第4~第8步；
5. 系统会在诊断记录上保存 `last_feedback_type`、`last_feedback_iteration`、`continue_from_step`，用于前端展示“继续排查到第几轮/第几步”的进度；
6. 当新迭代完成后，若置信分 ≥ 阈值则照常结束；若仍不足则再次进入人机协同等待反馈。

**继续排查触发条件总结**：
- 反馈类型为 `continue_investigation`
- 当前诊断记录状态为 `completed` 或 `pending_human`
- 当前迭代已经执行完毕且存在置信分（避免并发触发）

**知识沉淀触发条件更新**：
- 若反馈类型为 `confirmed` 且知识库尚未生成对应案例，则立即调用 `save_diagnosis_to_knowledge_base` 保存完整报告，确保“确认的反馈”都会沉淀。

### 5.4 数据结构

#### 5.4.1 诊断记录 (diagnosis_records)

```python
{
    "id": 123,
    "cluster_id": 1,
    "namespace": "default",
    "resource_type": "pods",
    "resource_name": "my-app-xxx",
    "status": "running" | "completed" | "pending_human" | "failed",
    # 注意：pending_next 状态已废弃，不再进行多轮迭代
    "trigger_source": "manual" | "alert" | "schedule",
    "symptoms": {
        "root_cause": "...",
        "timeline": {...},
        "impact_scope": {...},
        "root_cause_analysis": {...},
        "evidence_chain": {...}
    },
    "metrics": {
        "iteration_1": {...},
        "iteration_2": {...}
    },
    "logs": {
        "iteration_1": {...},
        "iteration_2": {...}
    },
    "recommendations": {
        "solutions": {
            "immediate": [...],
            "root": [...],
            "preventive": [...]
        }
    },
    "summary": "...",
    "conclusion": "...",
    "confidence": 0.92,
    "knowledge_refs": [123, 456],
    "knowledge_source": "llm" | "kb" | "rules",
    "feedback": {
        "latest": {
            "feedback_type": "confirmed" | "continue_investigation" | "custom",
            "feedback_notes": "...",
            "action_taken": "...",
            "iteration_no": 1,
            "submitted_at": "2025-01-01T10:00:00Z"
        },
        "history": [
            {
                "feedback_type": "...",
                "iteration_no": 1,
                "continue_from_step": 2
            }
        ]
    },
    "feedback_state": {
        "last_feedback_type": "continue_investigation",
        "last_feedback_iteration": 1,
        "continue_from_step": 2,
        "min_steps_before_exit": 3
    }
}
```

#### 5.4.2 迭代记录 (diagnosis_iterations)

```python
{
    "id": 456,
    "diagnosis_id": 123,
    "iteration_no": 1,
    "stage": "iteration_1",
    "status": "completed",
    "reasoning_prompt": "...",
    "reasoning_summary": "...",
    "reasoning_output": {
        "rule_findings": [...],
        "knowledge_refs": [...],
        "llm_result": {...},
        "root_cause_analysis": {...},
        "evidence_chain": {...}
    },
    "action_plan": [...],
    "action_result": [...]
}
```

#### 5.4.3 上下文记忆 (diagnosis_memories)

```python
{
    "id": 789,
    "diagnosis_id": 123,
    "iteration_id": 456,
    "iteration_no": 1,
    "memory_type": "metric" | "log" | "rule" | "knowledge" | "search" | "llm" | "conclusion" | "symptom" | "error" | "k8s_resource" | "deep_context" | "api_data" | "change_event",
    "summary": "...",
    "content": {...}
}
```

### 5.5 关键配置参数

**配置文件**：`app/config/settings.py`

```python
# 诊断迭代配置
OBSERVABILITY_DIAGNOSIS_MAX_ITERATIONS = 5          # 最大迭代次数（已废弃，不再使用）
OBSERVABILITY_DIAGNOSIS_CONFIDENCE_THRESHOLD = 0.8  # 置信度阈值
OBSERVABILITY_DIAGNOSIS_MEMORY_RECENT_LIMIT = 10    # 最近记忆条数
OBSERVABILITY_DIAGNOSIS_ITERATION_DELAY_SECONDS = 5 # 迭代延迟（已废弃，不再使用）

# 数据收集配置
OBSERVABILITY_METRICS_CACHE_SECONDS = 300           # 指标缓存时间
OBSERVABILITY_LOG_CACHE_SECONDS = 300               # 日志缓存时间

# LLM 配置
LLM_DIAGNOSIS_ENABLED = True                        # 是否启用 LLM
OLLAMA_MODEL = "llama3"                             # LLM 模型名称

# 外部搜索配置
SEARXNG_URL = "http://searxng:8080"                 # Searxng 地址
```

### 5.6 API 接口

#### 5.6.1 触发诊断

**POST** `/api/v1/observability/diagnosis/run`

**请求体**：
```json
{
    "cluster_id": 1,
    "namespace": "default",
    "resource_type": "pods",
    "resource_name": "my-app-xxx",
    "trigger_source": "manual"
}
```

#### 5.6.2 获取诊断记录

**GET** `/api/v1/observability/diagnosis/{id}`

**响应**：包含诊断记录、迭代历史、上下文记忆

#### 5.6.3 提交反馈

**POST** `/api/v1/observability/diagnosis/{id}/feedback`

**请求体**：
```json
{
    "feedback_type": "confirmed",
    "feedback_notes": "已确认是 ZooKeeper 地址配置错误",
    "action_taken": "已回滚 Service 配置"
}
```
- `feedback_type`：必填，枚举值 `confirmed` / `continue_investigation` / `custom`
- `feedback_notes`：可选文本；当类型为 `custom` 或 `continue_investigation` 时强制要求填写
- `action_taken`：可选文本（如“已重启 Pod”）

**接口行为**：
1. 保存反馈内容与类型至诊断记录，并写入反馈记忆；
2. `confirmed`：若尚未沉淀到知识库，立即调用 `save_diagnosis_to_knowledge_base`，并记录 `knowledge_sedimented = true`；
3. `continue_investigation`：设置 `llm_confidence_step1 = 0.5`，记录 `continue_from_step`，创建新的迭代并强制执行至少 3 个步骤；
4. `custom`：只记录反馈文本，不触发额外流程。

#### 5.6.4 获取迭代历史

**GET** `/api/v1/observability/diagnosis/{id}/iterations`

#### 5.6.5 获取上下文记忆

**GET** `/api/v1/observability/diagnosis/{id}/memories`

### 5.7 异常处理

**数据收集失败**：
- 指标收集失败：记录警告，继续执行其他动作
- 日志收集失败：尝试回退策略（K8s API → 日志系统）
- 知识库搜索失败：记录警告，继续执行

**LLM 调用失败**：
- 回退到纯规则引擎和知识库推荐
- 记录失败原因到诊断记录

**迭代失败**：
- 记录失败原因
- 如果连续失败，状态更新为 `failed`
- 通知运维人员

### 5.8 LLM 推理增强：系统化根因分析

**增强后的 Prompt 模板**：
```
你是一名 Kubernetes 运维专家，请使用系统化的方法分析问题：

## ⚠️ 重要原则：日志优先原则
- **必须优先分析日志中的错误信息**，这是诊断问题的直接证据
- 如果日志中有明确的错误（如 UnknownHostException、Connection refused、Timeout 等），
  必须直接使用这些错误信息作为根因，而不是推测配置问题
- 避免在没有证据的情况下推测配置问题（如 setup.sh 脚本错误）

## 1. 问题描述
清晰描述当前问题（What）

## 2. 时间线分析（When）
- 问题何时开始？
- 问题何时恶化？
- 关键事件时间点

## 3. 影响范围（Where）
- 哪些资源受影响（Pod/Service/Node）？
- 业务影响程度（高/中/低）？

## 4. 5 Why 根因分析（Why）
- 为什么1（直接原因）：优先使用日志中的错误信息
- 为什么2：...
- 为什么3：...
- 为什么4：...
- 为什么5（根本原因）：...

## 5. 证据链（优先级：日志 > 指标 > 配置 > 事件）
- 日志证据：**优先分析**，包含明确的错误信息（如 UnknownHostException、Connection refused 等）
- 指标证据：...
- 配置证据：...
- 事件证据：...

## 6. 根因结论
基于证据链得出的根因（置信度：0-1）
- 如果日志中有明确的错误信息，直接使用作为根因，置信度应 >= 0.85

## 7. 解决方案（How）
### 立即缓解措施（治标）
- 操作步骤：...
- 风险评估：...
- 回滚方案：...

### 根本解决方案（治本）
- 操作步骤：...
- 风险评估：...
- 验证方法：...

### 预防措施
- 建议：...

请以 JSON 格式返回上述分析结果。
```

**输出格式**（结构化）：
```python
{
    "problem_description": "Pod 频繁重启，CPU 使用率持续高位",
    "timeline": {
        "problem_start": "2024-01-01T10:00:00Z",
        "problem_escalate": "2024-01-01T10:15:00Z",
        "key_events": [...]
    },
    "impact_scope": {
        "affected_pods": ["pod-1", "pod-2"],
        "affected_services": ["service-1"],
        "business_impact": "high"
    },
    "root_cause_analysis": {
        "why1": "Pod CPU 使用率达到 95%",
        "why2": "应用处理请求过多",
        "why3": "没有设置资源限制",
        "why4": "部署配置不完整",
        "why5": "缺少资源配额管理流程（根本原因）"
    },
    "evidence_chain": {
        "metrics": {"cpu_usage": 0.95, "restart_count": 5},
        "logs": ["ERROR: Out of memory"],
        "config": {"resources": null}
    },
    "root_cause": "Pod 缺少资源限制配置，导致资源耗尽后重启",
    "confidence": 0.92,
    "solutions": {
        "immediate": [...],
        "root": [...],
        "preventive": [...]
    },
    "next_action": "completed" | "collect_more_logs" | "pending_human"
}
```

### 5.9 深度诊断详细信息（已废弃）

**注意**：以下内容为原多轮迭代设计的一部分，现已废弃。单轮迭代内已完成所有8个诊断步骤，如果置信分仍<0.8，直接申请人工介入，不再进行深度诊断收集。

**说明**：
- 原设计中，深度诊断信息会在下一轮迭代中收集（如Events、同一Deployment的其他Pod、更长时间范围的指标等）
- 优化后：单轮迭代内已尝试所有可能的诊断方法（模型分析、知识库搜索、扩展K8s信息、外部搜索等）
- 如果经过8个步骤后，置信分仍<0.8，说明问题复杂，需要人工专家介入，不再自动收集更多信息

**保留原因**：此章节保留用于历史参考，或作为未来扩展的参考。实际实现中，这些信息可在人工介入时由专家指导收集。

#### 5.9.1 K8s Events（集群事件）⭐

**目的**：通过事件历史了解资源的变化过程，找出问题发生的时间点和原因

**收集内容**：

**Pod 相关事件**：
- 来源：`/api/v1/namespaces/{namespace}/events`
- 过滤条件：`involvedObject.kind == "Pod" && involvedObject.name == {pod_name}`
- 收集字段：事件类型、原因、消息、首次/最后发生时间、发生次数
- 数量：最近 20 条事件
- 分析价值：
  - `FailedScheduling` → 调度问题（节点资源不足、污点等）
  - `Unhealthy` → 健康检查失败
  - `BackOff` → 容器启动失败
  - 通过时间序列可以找出问题开始的时间点

**相关资源事件**：
- 过滤条件：`involvedObject.kind in ["Deployment", "StatefulSet", "Node", "ReplicaSet"]`
- 数量：最近 20 条事件
- 分析价值：
  - Deployment 事件：了解是否有扩缩容、滚动更新等操作
  - Node 事件：了解节点是否有故障、维护等
  - ReplicaSet 事件：了解副本集的变化

#### 5.9.2 同一 Deployment/StatefulSet 下的其他 Pod ⭐

**目的**：通过对比分析，判断是特定 Pod 的问题还是控制器/配置的问题

**收集方式**：
1. 从 Pod 的 `ownerReferences` 获取 Deployment/StatefulSet 名称
2. 查询同一命名空间下的所有 Pod
3. 筛选出属于同一个控制器的 Pod

**收集内容**：Pod 名称、状态（phase）、所在节点、条件（conditions）

**分析价值**：
- 如果其他 Pod 都正常 → 特定 Pod 的问题（可能是节点问题、资源竞争等）
- 如果其他 Pod 也异常 → 控制器或配置的问题（Deployment 配置、ConfigMap、镜像等）
- 如果所有 Pod 都在同一节点异常 → 节点级别的问题

#### 5.9.3 同一节点上的其他 Pod ⭐

**目的**：判断是否是节点级别的问题（资源不足、节点故障等）

**收集方式**：
1. 从 Pod 的 `spec.nodeName` 获取节点名称
2. 查询集群中所有 Pod（跨命名空间）
3. 筛选出运行在同一节点上的 Pod（最多 20 个）

**分析价值**：
- 如果节点上其他 Pod 都正常 → 不是节点级别的问题
- 如果节点上多个 Pod 都异常 → 节点级别的问题（CPU/内存不足、网络、存储、kubelet 故障等）
- 如果节点上系统 Pod（kube-system）异常 → 节点基础设施有问题

#### 5.9.4 命名空间级别的统计信息

**收集内容**：命名空间下的 Pod 总数、各状态的 Pod 数量（Running、Pending、CrashLoopBackOff、Error 等）

**分析价值**：
- 如果命名空间下大量 Pod 异常 → 可能是命名空间级别的问题（ResourceQuota、NetworkPolicy 等）
- 如果只有少数 Pod 异常 → 特定 Pod 的问题

#### 5.9.5 更长时间范围的指标和日志 ⭐

**目的**：通过分析更长时间范围的数据，找出问题发生前后的趋势变化，定位问题开始的确切时间点

**指标时间范围**（原设计中）：
- 默认：30 分钟（第一轮诊断）
- 深度诊断：2-4 小时（已废弃）
- 收集指标：CPU 使用率趋势、内存使用趋势、重启频率趋势
- 根据时间范围调整步长（1 分钟 / 5 分钟 / 15 分钟）

**日志时间范围**（原设计中）：
- 默认：15 分钟（第一轮诊断）
- 深度诊断：2-4 小时（已废弃）
- 收集方式：优先从日志系统（ELK/Loki）获取历史日志，如果日志系统不可用，从 K8s API 获取（如果 Pod 仍在运行）

**分析价值**：
- 找出问题开始的时间点
- 分析问题发生前后的趋势变化
- 判断是突发问题还是渐进式问题
- 找出错误日志首次出现的时间

#### 5.9.6 历史对比分析 ⭐

**目的**：通过对比问题发生前后的变化，找出导致问题的根本原因

**配置变化对比**：
- 数据来源：`resource_snapshots` + `resource_events` 表的历史记录
- 对比对象：Pod 配置变化（spec、labels、annotations）、Deployment/StatefulSet 配置变化、ConfigMap/Secret 配置变化
- 对比时间范围：问题发生前 24 小时
- 分析价值：找出最近是否有配置变更，判断配置变更是否导致问题，提供回滚建议

**配置变更过滤与排序策略（当前实现）**：
- 目标：在 24 小时内可能有大量变更时，**优先找出与当前故障最相关的那一小部分**，避免“全量扔给 LLM”。
- **时间维度（Time）**：
  - 以本次诊断的触发时间 / 记录创建时间作为参考点 \(T\)。
  - 优先关注距离 \(T\) 最近的变更（例如 \(T\) 前后 5~30 分钟），其次是 \(T\) 前 1~2 小时，更早的变更权重逐渐降低。
- **作用范围（Scope）**：
  - 只查询**同一命名空间**的相关资源变更：
    - 目标资源本身（Pod / Node / Service / Deployment 等）的变更；
    - 同一命名空间下的 `ConfigMap`、`Secret`、`Deployment`、`StatefulSet`、`DaemonSet` 等变更。
  - 后续可以基于 Pod 的 `ownerReferences`、`volumes`、`envFrom` 等信息，进一步收缩到**真实依赖链上的资源**（当前版本先按命名空间 + 资源类型过滤）。
- **事件类型（EventType）**：
  - 只保留与配置相关的事件：
    - `created`：新建配置（例如新建 ConfigMap / Deployment）；
    - `updated`：配置更新（spec / data 等发生变化）。
  - 忽略 `deleted` 等对当前故障相关性较弱的事件（后续可按需放开）。
- **风险权重（Risk Score）**：
  - 对不同资源类型和变更内容赋予不同权重（越可能导致故障，权重越高）：
    - 高：`Deployment/StatefulSet` 的 `spec` 变更、Pod 的资源限制 / 探针 / 镜像变更、被当前工作负载使用的 `ConfigMap/Secret` 变更；
    - 中：`DaemonSet`、`Service`、`NetworkPolicy`、`ResourceQuota` 相关变更；
    - 低：仅 Label / Annotation 等元数据变更。
- **综合打分与截断**：
  - 为每条变更计算一个综合分数（时间接近程度 + 资源类型风险 + 事件类型），按分数**从高到低排序**；
  - 最终只保留前 N 条高分变更（例如最多 100 条，并在 LLM Prompt 中展示前 20 条），其余变更不进入 LLM 上下文，以控制上下文长度并聚焦关键信息。
- **LLM 使用方式**：
  - 将排序后的变更列表以结构化形式加入 Prompt，明确提示 LLM：
    - 结合变更时间与故障发生时间，判断是否存在明显因果关系；
    - 优先检查 Deployment/Pod/ConfigMap/Secret 等配置变更是否可以解释当前症状；
    - 如果变更与故障无明显关联，也要明确说明“不太可能由最近的配置变更引起”，避免误判。

**指标数据对比**：
- 数据来源：Prometheus 历史数据
- 对比方式：对比问题发生前后的指标趋势，对比历史同期（如昨天同一时间）的指标数据
- 对比指标：CPU 使用率、内存使用率、重启频率、网络流量
- 分析价值：判断指标是否异常，找出指标异常的时间点，判断是否是周期性或突发性问题

**资源状态对比**：
- 数据来源：`resource_snapshots` 表的历史记录
- 对比对象：Pod 状态变化（phase、conditions）、节点状态变化、资源使用情况变化
- 分析价值：找出状态变化的时间点，关联配置变更和状态变化，判断问题的因果关系

#### 5.9.7 深度诊断示例场景

**场景1：节点资源不足**
- 事件：`FailedScheduling: 0/3 nodes available: 3 Insufficient cpu`
- 同一节点上的其他 Pod：节点上 15 个 Pod，其中 10 个处于 Pending 状态
- 分析结论：节点 CPU 资源不足，导致 Pod 无法调度

**场景2：镜像拉取失败**
- 事件：`Failed: Error: ImagePullBackOff: Failed to pull image "my-app:v1.0"`
- 同一 Deployment 的其他 Pod：3 个 Pod 都处于 `ImagePullBackOff` 状态
- 分析结论：镜像拉取失败，影响整个 Deployment

**场景3：ConfigMap 配置错误**
- 事件：`Warning: Unhealthy: Readiness probe failed`
- 同一 Deployment 的其他 Pod：3 个 Pod 都处于 `CrashLoopBackOff` 状态
- 分析结论：可能是 ConfigMap 配置错误，导致所有 Pod 启动失败

## 6. 标准运维诊断流程评估

### 6.1 标准运维诊断流程（业界最佳实践）

标准流程包括：问题发现 → 数据收集 → 问题定位 → 根因分析 → 解决方案 → 验证和反馈 → 知识沉淀

### 6.2 当前流程评估

| 标准流程阶段 | 当前实现 | 完整度 | 说明 |
|------------|---------|--------|------|
| **1. 问题发现** | ✅ | 90% | 支持告警触发、手动触发 |
| **2. 数据收集** | ✅ | 90% | 指标、日志（混合策略）、K8s 资源（第一层扩展） |
| **3. 问题定位** | ✅ | 80% | 时间线分析、影响范围评估、关联分析 |
| **4. 根因分析** | ✅ | 85% | 系统化分析方法（5 Why、证据链）、LLM 推理 |
| **5. 解决方案** | ✅ | 85% | 结构化解决方案（可执行步骤、优先级排序、风险评估） |
| **6. 验证和反馈** | ⚠️ | 40% | 有反馈机制，缺少自动验证 |
| **7. 知识沉淀** | ⚠️ | 50% | 需要人工确认，缺少自动沉淀 |

### 6.3 已实现的核心功能

✅ **系统化根因分析**：5 Why 分析法、证据链构建、假设验证  
✅ **结构化解决方案**：可执行步骤、优先级排序、风险评估、回滚方案  
✅ **完整诊断流程**：单轮迭代内完成8个诊断步骤（模型分析、知识库搜索、扩展K8s信息、外部搜索等）  
✅ **上下文记忆**：跨步骤的事实和结论管理  
✅ **扩展诊断范围**：K8s 资源收集（第一层扩展）  
✅ **历史对比分析**：配置变化、指标对比、状态对比  

### 6.4 待增强的功能

⚠️ **问题验证机制**：诊断结果验证、解决方案效果验证  
⚠️ **知识沉淀自动化**：自动知识提取、知识质量评估  
⚠️ **更丰富的规则引擎**：当前只有基础规则  
⚠️ **诊断结果自动通知**：邮件/钉钉/飞书  
⚠️ **支持更多资源类型**：当前主要针对 Pod

## 7. 安全与权限
- Kubernetes 访问凭证使用最小权限原则（只读或特定命名空间）。
- Prometheus / Alertmanager API 若暴露在公网，应通过反向代理和鉴权保护。
- 重要配置（Token、证书）加密存储，操作全程审计记录。
- 支持按集群/团队划分权限，避免未授权人员访问敏感数据。

## 8. 部署架构建议
- **平台主体**：可运行在容器或虚拟机上，与目标集群通信。
- **高可用**：关键组件（同步、告警处理）支持多实例部署，通过消息队列或数据库实现状态共享。
- **存储**：使用关系型/时序数据库保存分析结果、执行日志；必要时缓存热点数据（Redis）。
- **监控自身**：平台也需要暴露指标，接入 Prometheus 监控自身健康状况。

## 9. 迭代规划（示例）
1. **MVP**：手动指定 Pod → 查询 Kubernetes 状态 + Prometheus 指标 → 输出诊断报告。
2. **Integration**：接入 Alertmanager Webhook，自动触发诊断流程；支持多集群。
3. **扩展**：引入日志检索、事件时间线展示、规则引擎；支持配置化阈值。
4. **智能化**：引入异常检测算法、自动化修复建议、历史案例库。
5. **知识库联动**：形成诊断经验闭环，支持推荐历史案例、自动生成知识条目。

## 10. 风险与注意事项
- 指标拉取频率 & Prometheus 性能：需控制调用频率，使用缓存，避免对监控系统造成压力。
- Kubernetes API Watch 的稳定性：需要处理连接断开、资源版本过期等情况。
- 跨集群统一：不同集群的指标标签、告警规则可能不一致，需抽象统一模型。
- 安全合规：敏感日志、配置数据须做脱敏与访问控制，满足企业安全要求。
- 大规模数据治理：需要规划 Prometheus 分片、远程存储以及日志索引与归档策略，防止十万级 Pod 带来的单点瓶颈。

## 11. 知识库集成设计
- **知识对象**：
  - 告警与诊断案例：记录告警标签、指标表现、诊断结论、处理步骤。
  - 历史事故复盘：包括时间线、根因、影响范围、恢复动作。
  - Runbook/FAQ：标准化操作流程、常见问题处理指南。
  - 架构与配置文档：业务依赖、资源配额、关键注意事项。
- **数据采集**：
  - 诊断模块产出的报告通过现有 `spx-knowledge-backend` 知识库接口入库，结构化存储事件信息与结论。
  - 运维人员可复用已有后台能力补充备注、上传复盘文档，完善知识条目。
  - 定期从外部系统（Wiki、工单平台）导入内容，统一标签规范。
- **索引与检索**：
  - 以 `cluster`、`namespace`、`service`、`alertname`、`指标模式` 等字段建索引。
  - 可在知识库现有接口之上扩展向量检索/语义搜索，支持自然语言查询和相似案例推荐。
  - 知识条目关联 Prometheus 标签、日志查询语句，便于快速跳转。
- **诊断联动**：
  - 告警触发自动匹配相关知识条目，为运维提供参考方案。
  - 处理结束后对推荐知识条目打分反馈，持续优化推荐效果。
  - 未命中的场景，引导运维创建新条目，形成闭环。
- **安全与治理**：
  - 知识条目按业务线/集群/敏感级别控制访问权限。
  - 对敏感信息（账号、凭证）做脱敏处理；记录查看/编辑审计日志。
  - 支持版本控制与审批流程，保证知识准确性与可追溯性。
- **实现路径**：
  1. 整合现有 `spx-knowledge-backend` API，梳理所需字段与权限；
  2. 将诊断报告、告警信息结构化写入知识库；
  3. 前端提供检索、推荐、反馈界面；
  4. 逐步加入智能推荐、问答机器人等高级功能。

## 12. 模型与知识库融合策略
- **分层诊断流程**：
  1. 首先查询知识库，若命中高相关条目则直接返回标准化结论；
  2. 未命中时，将告警上下文（指标摘要、配置、日志片段）交给大模型推理；
  3. **联网搜索触发条件**：若知识库未命中 **且** 模型回复的置信度低于阈值（默认 0.8），再调用 searxng 等搜索引擎检索外部资料，获取权威来源后由模型综合总结。
  4. 如果进行了外部搜索，使用外部搜索结果重新调用模型，提升诊断准确性。
- **知识沉淀闭环**：
  - 模型或搜索得出的有效结论，由人工确认后写入知识库，逐步减少“未知问题”；
  - 记录每次诊断的来源（知识库/模型/搜索）与成效评分，优化推荐策略。
- **安全与脱敏**：
  - 联网检索前对日志、配置等敏感信息脱敏处理，避免泄露；
  - 对模型输入输出加审计，关键结论须人工确认。
- **智能化方向**：
  - 搭建领域向量检索库，辅助大模型更快定位知识；
  - 根据告警类别动态选择 prompt 模板或专用模型，提升准确率；
  - 利用反馈数据迭代模型或规则，持续提升诊断效果与置信度。

## 13. 数据模型与存储设计
- **cluster_config**（集群配置表）：
  | 字段 | 类型 | 说明 |
  | --- | --- | --- |
  | id | UUID | 主键 |
  | name | text | 集群名称 |
  | api_server | text | Kubernetes API 地址 |
  | auth_type | enum | kubeconfig / token / cert |
  | credential_ref | text | 指向密钥存储位置的引用 |
  | prometheus_url | text | Prometheus 地址 |
  | log_endpoint | text | 日志系统入口 |
  | status | enum | active / disabled / error |
  | last_health_check_at | timestamp | 最近联通性检测时间 |
  | created_at / updated_at | timestamp | 创建 / 更新时间 |
- **resource_snapshot**（资源快照表）：
  | 字段 | 类型 | 说明 |
  | resource_uid | text | Kubernetes UID |
  | cluster_id | UUID | 所属集群 |
  | kind | text | 资源类型（Pod/Deployment 等） |
  | namespace | text | 命名空间 |
  | name | text | 资源名 |
  | labels / annotations | jsonb | 标签和注解 |
  | spec | jsonb | 原始 spec（脱敏后） |
  | status | jsonb | 当前状态 |
  | resource_version | text | 资源版本 |
  | fetched_at | timestamp | 同步时间 |
- **diagnosis_record**（诊断记录表）：
  | 字段 | 类型 | 说明 |
  | id | UUID | 主键 |
  | trigger_source | enum | alert / manual / schedule |
  | cluster_id | UUID | 集群 |
  | namespace | text | 命名空间 |
  | pod | text | 目标 Pod |
  | symptoms | jsonb | 指标摘要、日志摘要 |
  | conclusion | jsonb | 诊断结论、置信度 |
  | evidence_refs | jsonb | 指标、日志、知识条目引用 |
  | knowledge_source | enum | kb / llm / search |
  | status | enum | open / resolved / pending |
  | created_at / resolved_at | timestamp | 时间戳 |
- **knowledge_entry**（知识库条目表）：
  | 字段 | 类型 | 说明 |
  | id | UUID | 主键 |
  | title | text | 标题 |
  | tags | text[] | 标签（cluster、service、alertname 等） |
  | summary | text | 摘要 |
  | content | text | 详细内容（Markdown） |
  | references | jsonb | 指向外部文档/诊断记录 |
  | confidence | numeric | 置信度/有效性评分 |
  | status | enum | published / draft / archived |
  | created_by | text | 创建人 |
  | created_at / updated_at | timestamp | 时间戳 |
- 按需扩展审计日志、模型调用日志等表。

## 14. 核心流程时序
- **告警驱动诊断**：
  1. Alertmanager 推送告警 → 告警处理模块接收并校验；
  2. 资源同步模块返回目标资源最新状态；日志模块提取最近 N 分钟日志摘要；
  3. 指标模块查询关键指标 → 规则引擎 + 知识库/模型做分析；
  4. 生成诊断报告，推送到通知渠道，并写入 `diagnosis_record`；
  5. 运维确认后可将结论沉淀到知识库或追加反馈。
- **手动诊断**：
  1. 运维通过前端选择集群/命名空间/Pod；
  2. 后端同步调用资源、指标、日志接口；
  3. 返回实时指标图、事件列表、推荐知识条目；支持继续执行深度分析。
- **配置接入与健康检查**：
  1. 用户在前端录入集群配置，提交后立即触发联通性测试；
  2. 测试任务通过后端依次访问 API Server、Prometheus、日志系统；
  3. 将测试结果展示给用户，并更新 `cluster_config.status`；
  4. 后端定时任务每日复查，失败时提醒运维。
- **知识库闭环**：
  1. 诊断完成后将结论、上下文写入知识库候选区；
  2. 审核人员确认内容无误后发布；
  3. 下一次同类告警自动命中该知识条目，减少模型调用。

## 15. 下一阶段工作重点
- **详细方案拆解**：为资源同步、指标查询、告警处理、知识库集成等模块补充接口定义、数据模型、时序图。
- **任务排期**：根据迭代规划制定开发里程碑，明确 MVP（V1）交付范围与验收标准。
- **环境准备**：确定目标集群、Prometheus、日志系统与知识库的测试环境，准备测试凭证和示例数据。
- **研发基线**：搭建代码仓库、CI/CD、基础镜像（含 Python 3.11、CUDA 等）与开发规范。
- **风险预案**：评估指标拉取、外部依赖、权限管理的潜在问题，制定应对策略。
- **评审与启动**：组织设计评审，确认所有干系人达成一致后启动开发。

---

## 16. 相关文档

- **实现方案与优化（核心实现文档）**：`docs/implementation-and-optimization.md`
  - 变更关联分析与资源事件追踪（含 MySQL + OpenSearch 双写）
  - 配置变更过滤与排序策略（与第 5.9.6 节对应的实现细节）
  - 大规模数据优化与保留策略

- **代码合规报告（总览）**：`docs/code-compliance-report.md`
  - 汇总各次代码检查结论
  - 记录与设计文档的符合度及已修复问题

- **最新详细检查报告**：`docs/code-compliance-check-final-2025-01.md`
  - 按当前统一设计文档逐项检查代码实现
  - 说明 95%+ 符合度和少量可选优化点（如 `diagnosis_k8s_collector` 的资源类型扩展）

---

该设计作为后续实现的基础，可在具体开发前进一步细化每个模块的接口定义、数据结构和部署细节。

