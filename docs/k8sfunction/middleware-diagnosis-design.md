# 中间件诊断设计说明（Nacos / MySQL / Zookeeper / Kafka / Redis / Keepalived / HAProxy / OpenSearch）

> 目标：在现有“K8s 统一诊断流程”的基础上，针对常见中间件集群补充专用规则和 LLM Prompt 模板，实现更精准的问题诊断。

---

## 1. 设计目标与原则

- **目标**：
  - 利用已有的 K8s + 指标 + 日志收集能力，对常见中间件的集群问题做出更有针对性的判断；
  - 将中间件的典型问题模式（配置 / 资源 / 版本 / 拓扑 / 高可用）沉淀为规则与 Prompt 模板。
- **原则**：
  - **不改诊断主流程**：仍使用统一的多轮诊断流程（收集数据 → 规则 → 知识库 → LLM → 多轮迭代）。
  - **按“中间件类型”做差异化**：通过 Pod / Deployment / StatefulSet 的 label/annotation 识别中间件类型，加载对应规则与 Prompt 片段。
  - **优先 K8s 视角**：优先利用 K8s/PVC/Service/ConfigMap/Secret/Node/Events + 指标/日志，避免必须依赖中间件内部管理命令。

---

## 2. 通用设计思路

### 2.1 中间件识别方式

- 基于 K8s 对象的标签/注解：
  - 如：`app=nacos`、`app=mysql`、`app=redis`、`component=zookeeper`、`app=kafka` 等。
- 支持配置化映射：
  - `middleware.type = nacos/mysql/zookeeper/kafka/redis/keepalived/haproxy/opensearch`
  - `middleware.role = master/slave/sentinel/broker/coordination/proxy` 等。

在诊断入口（Pod / StatefulSet / Deployment）中识别到这些标签后：

- 在 **规则引擎** 中加载对应的中间件规则集；
- 在 **LLM Prompt** 中增加中间件专用说明和常见故障模式提示。

### 2.2 诊断信息来源（通用）

所有中间件共用的数据来源：

- **K8s API**：
  - Pod / StatefulSet / Deployment / Service / ConfigMap / Secret / PVC / Node / Events / ResourceQuota / NetworkPolicy。
- **Prometheus 指标**：
  - K8s 基础指标：CPU、内存、磁盘、重启次数、网络流量；
  - 中间件专用指标（如果有 exportor）：
    - 如：`redis_connected_clients`、`mysql_global_status_*`、`kafka_server_*` 等。
- **日志系统**：
  - 中间件 Pod 日志：错误堆栈、连接失败、超时、心跳失败、选主过程日志等。
- **资源变更记录**：
  - StatefulSet/Deployment/ConfigMap/Secret 等的配置变更；
  - 镜像变更、资源限制变更、环境变量变更。

---

## 3. 各中间件诊断要点

### 3.1 Nacos

- **典型部署形态**：
  - StatefulSet + Service + MySQL（持久化元数据）；
- **主要问题类型**：
  - 配置：
    - 数据库连接配置错误（ConfigMap/Secret）
    - 集群节点地址配置错误；
  - 资源：
    - Nacos 节点 CPU/内存过高导致响应慢；
  - 版本 / 发布：
    - 升级后注册中心/配置中心异常。
- **规则要点**：
  - Nacos Pod 日志中出现数据库连接失败 / 心跳失败 / 注册失败；
  - 所有 Nacos Pod 同时重启或同时健康探针失败；
  - MySQL Pod/PVC/Service 异常导致 Nacos 不可用。
- **Prompt 补充**：
  - 说明这是“配置中心 + 注册中心”，引导 LLM：
    - 检查数据库连接配置及状态；
    - 检查 Nacos 集群节点之间的连接和心跳；
    - 关注升级/变更时间点与故障的关系。

### 3.2 MySQL

- **典型部署形态**：
  - StatefulSet（主从、MGR 等）+ Service + PVC；
- **主要问题类型**：
  - 资源：CPU/内存/磁盘打满，IO 延迟高；
  - 配置：max_connections 太小、缓冲区配置不合理；
  - 版本/升级：升级后连接异常或 SQL 行为变化；
  - 存储：PVC 状态异常、磁盘只读/空间不足。
- **规则要点**（K8s 视角）：
  - Pod 日志中出现 `Too many connections`、`InnoDB` 错误、磁盘错误；
  - PVC 中出现 `Filesystem read-only`、`Volume` 挂载失败事件；
  - 同一 StatefulSet 下多个 Pod 异常/重启。
- **Prompt 补充**：
  - 提示 LLM：
    - 结合 PVC、磁盘指标判断是否为存储问题；
    - 结合 ConfigMap/环境变量变更判断是否为配置/版本问题；
    - 当日志中出现典型 MySQL 错误时，联想到连接池/慢查询/锁等常见原因（仅从日志表象推理）。

### 3.3 Zookeeper

- **典型部署形态**：
  - StatefulSet + Headless Service；
- **主要问题类型**：
  - 选主失败、quorum 不够；
  - 网络抖动导致 session 频繁断开；
  - 磁盘 IO 问题。
- **规则要点**：
  - Pod 日志包含 `LEADING`/`FOLLOWING` 切换异常、`Too many connections`、`Session expired`；
  - 多个 Zookeeper Pod 同时异常或频繁重启。
- **Prompt 补充**：
  - 强调其作为“协调服务”的角色，引导输出：
    - 集群不可用是否由 leader 选举/节点少于半数导致；
    - 是否由网络/节点级问题引起；
    - 配置变更是否触发了拓扑变化。

### 3.4 Kafka

- **典型部署形态**：
  - StatefulSet + Service + Zookeeper（或 KRaft 模式）；
- **主要问题类型**：
  - 资源：磁盘空间不足、网络带宽不足；
  - 配置：分区/副本配置不合理；
  - 集群：ISR 缩水、控制器异常；
  - 下游：消费者/生产者异常。
- **规则要点**（K8s 视角）：
  - Kafka Pod 日志中的 `Leader not available`、`Replica not available`、`Request timed out` 等；
  - 多个 Kafka Pod 重启/CrashLoopBackOff；
  - 磁盘/PVC 指标异常。
- **Prompt 补充**：
  - 引导 LLM：
    - 将 Kafka 的错误与 Zookeeper/磁盘/网络的状态关联；
    - 强调配置变更（副本数、分区数、保留策略）与故障时间的关系。

### 3.5 Redis（主从 / 哨兵 / 集群）

- **典型部署形态**：
  - 单实例 / 主从 + Sentinel / Cluster 模式，通常为 StatefulSet + Service；
- **主要问题类型**：
  - 资源：内存不足、连接数过多；
  - 高可用：主从切换异常、Sentinel 配置错误；
  - 集群槽分布异常、节点下线。
- **规则要点**：
  - Pod 日志中的 `OOM command not allowed`、`Master not reachable`、`Sentinel` 报警；
  - 所有 Redis 实例同时重启或同一组件（Sentinel/Master）异常；
  - PVC/节点资源问题影响 Redis。
- **Prompt 补充**：
  - 引导 LLM：
    - 对集群/哨兵模式给出更有针对性的判断（主从切换是否成功、Sentinel 是否可达）；
    - 将内存/连接数指标和配置（maxmemory、maxclients）联系起来分析。

### 3.6 Keepalived

- **典型部署形态**：
  - DaemonSet 或 Deployment + HostNetwork；
- **主要问题类型**：
  - VIP 漂移异常、抢占配置错误；
  - 健康检查命令配置错误。
- **规则要点**：
  - 日志中 `STATE` 切换频繁、健康检查脚本失败；
  - 同一 Node 上多个依赖 Keepalived 的服务异常。
- **Prompt 补充**：
  - 强调 Keepalived 是虚拟 IP 高可用组件，引导 LLM 把 VIP 漂移/健康检查失败与后端服务故障关联起来。

### 3.7 HAProxy

- **典型部署形态**：
  - Deployment/DaemonSet + Service；
- **主要问题类型**：
  - 后端服务器健康检查失败；
  - 连接数打满、队列堆积。
- **规则要点**：
  - 日志中 5xx 比例升高、后端服务 Unhealthy；
  - HAProxy Pod 资源瓶颈。
- **Prompt 补充**：
  - 引导 LLM 从“代理 + 后端服务”的组合视角分析：是 HAProxy 自身问题，还是后端实例问题。

### 3.8 OpenSearch

- **典型部署形态**：
  - StatefulSet 集群 + Service + PVC；
- **主要问题类型**：
  - 磁盘空间不足、Shard 分配失败；
  - 集群健康红黄、节点掉线；
  - 查询性能下降。
- **规则要点**：
  - Pod 日志中的 Shard 分配错误、磁盘 watermark 报警；
  - PVC 磁盘压力异常；
  - 多个节点同时 NotReady/重启。
- **Prompt 补充**：
  - 引导 LLM 将 OpenSearch 的集群健康状态（日志/指标）与磁盘/节点状态关联；
  - 特别分析最近的配置变更（副本数、shard 数、索引策略）对集群负载的影响。

---

## 4. 集成方式（规则 + Prompt）

### 4.1 规则引擎扩展

- 在 `DiagnosisRuleService` 中为每种中间件增加规则集：
  - `evaluate_nacos_rules(...)`
  - `evaluate_mysql_rules(...)`
  - `evaluate_zookeeper_rules(...)`
  - `evaluate_kafka_rules(...)`
  - `evaluate_redis_rules(...)`
  - `evaluate_keepalived_rules(...)`
  - `evaluate_haproxy_rules(...)`
  - `evaluate_opensearch_rules(...)`
- 根据 Pod/StatefulSet/Deployment 的标签识别中间件类型，并在 `evaluate()` 中动态选择规则集。

### 4.2 LLM Prompt 模板扩展

- 在 `DiagnosisLlmService.build_structured_llm_prompt()` 中：
  - 根据 context / labels 识别中间件类型；
  - 动态追加对应中间件的“常见问题类型 + 关键指标/日志特征 + 分析建议”段落；
  - 要求 LLM 在 5 Why / 证据链中显式考虑中间件自身的角色和特性。

---

## 5. 迭代计划（后续优化）

- **P0**：基于现有收集能力，先实现简单的中间件规则和 Prompt 补充（只用 K8s + 日志表象做诊断）；  
- **P1**：接入中间件 Exporter 指标（如果有），扩充规则（如连接数、慢查询、ISR、复制延迟等）；  
- **P2**：引入中间件内部管理接口（可选），在不破坏安全边界的前提下读取一定程度的内部状态，进一步提升诊断精度。

> 说明：本设计文档只定义“如何在现有 K8s 统一诊断框架上增强中间件诊断能力”，具体规则实现与 Prompt 细化将在后续迭代中按中间件逐步落地。***

