# K8s 运维诊断边界说明

> 本文档用于说明当前诊断系统的**能力范围和边界**，便于后续优化与扩展

---

## 1. 总体能力边界

- **诊断目标**：通过接入 **K8s API Server + Prometheus + 日志系统**，对 K8s 集群中的常见问题进行自动分析，给出**根因 + 解决方案 + 置信度**。
- **统一流程**：所有支持的资源类型（Pod、Node、Deployment、Service 等）共用一套多轮诊断流程：
  - 收集数据（API Server + 指标 + 日志）
  - 规则检测
  - 知识库搜索
  - LLM 推理（可选外部搜索）
  - 多轮迭代 + 扩展诊断范围 + 深度诊断
- **重要前提**：系统**只依赖 K8s API、Prometheus、日志系统提供的信息**，**不能访问集群外主机文件、系统命令输出等**。

---

## 2. 支持的诊断对象与当前能力

### 2.1 Pod（当前支持最完整）

- **可作为诊断入口**（`resource_type="pods"`）：
  - CrashLoopBackOff、频繁重启、镜像拉取失败、探针失败
  - CPU/内存异常、OOM、资源限制配置错误
  - ConfigMap/Secret 配置错误导致应用启动失败或行为异常
- **每轮收集的数据**：
  - API：Pod `spec/status/metadata`
  - 指标：`pod_cpu_usage`、`pod_memory_usage`、`pod_restart_rate`
  - 日志：混合策略（K8s API 实时日志 + 日志系统历史日志）
  - 最近 24 小时配置变更：Pod 自身 + 同命名空间 ConfigMap/Secret/Deployment/StatefulSet/DaemonSet
- **多轮扩展能力**：
  - 第 2 轮：收集相关 K8s 资源（Deployment/StatefulSet/DaemonSet、Service、ConfigMap/Secret、Node、ResourceQuota、NetworkPolicy、PVC）
  - 第 3 轮及以后：深度诊断（Events、同控制器下其他 Pod、同节点其他 Pod、命名空间统计、历史快照对比、指标历史对比）

> 结论：**Pod 级问题是当前系统的“一等公民”，诊断链路最完整、支持的场景最多。**

### 2.2 Node（节点级问题）

- **可作为诊断入口**（`resource_type="nodes"`）：
  - 节点 NotReady / Ready 状态频繁切换
  - 节点资源压力：CPU/内存/磁盘使用率持续过高
  - 通过 Node 状态 + 节点上大量 Pod 异常，间接判断节点级问题
- **每轮收集的数据**：
  - API：Node `status`（conditions、capacity、allocatable、addresses 等）
  - 指标：`node_cpu_usage`、`node_memory_usage`、`node_disk_usage`
  - 日志：节点相关日志（通过日志系统获取 Kubelet/系统日志）
- **当前不足**：
  - 扩展诊断和深度诊断逻辑仍以 Pod 为中心，针对 Node 的“相关资源收集”和“节点级深度诊断”还未单独设计。

### 2.3 Deployment / StatefulSet / DaemonSet（工作负载）

- **可作为诊断入口**（`resource_type="deployments"/"statefulsets"/"daemonsets"`）：
  - 副本数达不到期望
  - 滚动更新失败 / 镜像版本切换后 Pod 全部异常
- **每轮收集的数据**：
  - API：控制器 `spec/status`（replicas、availableReplicas、更新策略等）
  - 指标：`deployment_replica_count`（副本趋势）
  - 日志：从日志系统获取与该工作负载相关的日志（通过标签过滤）
- **通过 Pod 视角的辅助分析**：
  - 当以 Pod 为入口时，会收集其 Deployment/StatefulSet/DaemonSet 的历史快照，对比：
    - 副本数变更
    - 镜像版本变更

### 2.4 Service（服务发现问题）

- **可作为诊断入口**（`resource_type="services"`）：
  - Service 无 Endpoints 或 Endpoints 数量异常
  - 部分流量无法转发 / 访问延迟异常（需要结合指标/日志）
- **每轮收集的数据**：
  - API：Service `spec`（type、selector、ports）、Endpoints 信息
  - 指标：`service_connection_count`（或相关网络指标）
  - 日志：Service/代理相关日志（通过日志系统）
- **结合 Pod / Deployment 分析**：
  - 通过标签匹配找出该 Service 后端的 Pod、工作负载，综合判断是 Service 配置问题还是后端实例问题。

### 2.5 ConfigMap / Secret / 其他配置资源

- **当前定位**：**“关键影响因素”而非诊断入口**：
  - 通过 `resource_events` + `resource_snapshots` 跟踪 ConfigMap/Secret/Deployment 等配置的变更
  - 在 LLM Prompt 中以“最近配置变更”形式呈现，要求 LLM 分析变更是否与故障时间相关
- **典型场景**：
  - ConfigMap 改错导致所有 Pod 启动失败
  - Secret key 增删导致应用连接异常

### 2.6 ResourceQuota / NetworkPolicy / PVC 等

- **当前定位**：**辅助信息**，通过 Pod 入口间接诊断：
  - ResourceQuota：命名空间内大量 Pod Pending + 配额状态异常 → 推断为配额问题
  - NetworkPolicy：Service/POD 无法访问，结合 NetworkPolicy 规则变化推断网络策略问题
  - PVC：Pod 挂载失败、只读文件系统等 + PVC 状态异常 → 推断存储问题
- **注意**：暂未实现以这些资源为直接入口的专用诊断流程。

---

## 3. 不能/暂不支持直接诊断的场景

- **集群外的主机问题**：
  - 无法访问物理机 / 虚拟机上的本地文件、系统日志、`top`/`dmesg` 等命令输出
  - 只能通过 Node 状态、指标、节点上 Pod 的行为“间接判断”可能存在主机问题

- **K8s 控制面内部实现细节**：
  - 如 kube-apiserver 本地配置文件、etcd 存储内部状态、CNI/CSI 插件的节点本地配置
  - 若这些组件以 Pod/DaemonSet 形式运行，系统可以通过其 Pod 状态、日志、事件、ConfigMap 来间接分析
  - 但无法直接读取节点上的本地配置文件

- **业务层面逻辑错误**：
  - 代码 bug、业务逻辑错误等只能通过日志和现象间接判断，无法做白盒级别的业务分析

---

## 4. 多轮诊断与数据复用边界

- **每轮都会重新收集“当前时刻”的数据**：
  - API Server：当前资源状态和配置
  - 指标：当前时间窗口（默认 30 分钟 / 深度诊断 2 小时）
  - 日志：当前时间窗口（默认 15 分钟 / 深度诊断 2 小时）
- **所有轮的数据都会写入 `diagnosis_memories`**：
  - 包含每轮的指标、日志、规则发现、LLM 输出、K8s 资源、深度上下文、变更信息等
- **后续轮次通过“历史记忆 + 新数据”综合判断**：
  - LLM Prompt 中会带上前几轮的摘要（而不是重复原始数据），用于趋势和对比分析
  - 深度诊断中的历史对比（快照 + 指标）也是基于已存储的数据实现的

---

## 5. 后续优化方向（待实现）

> 以下内容是规划方向，当前代码未完全实现，后续迭代中逐步完善

1. **非 Pod 入口的扩展/深度诊断链路**  
   - 为 Node、Service、Deployment 等设计各自的“扩展诊断范围”和“深度诊断”收集策略  
   - 例如：以 Node 为入口时，自动收集该节点上的系统 Pod、CNI/CSI Pod、Kubelet 日志等

2. **更多资源类型作为诊断入口**  
   - ResourceQuota / NetworkPolicy / PVC 等支持 `resource_type` 直连入口  
   - 结合已有的配额状态、策略规则、存储状态，形成专门的规则和 LLM 模板

3. **控制面组件的专门诊断视图**  
   - 对 kube-apiserver / kube-controller-manager / kube-scheduler / etcd 等组件（如果以 Pod 形式部署）  
   - 提供专门的告警解析、事件分析和配置变更分析能力

4. **问题验证与闭环优化**  
   - 在保持“只做诊断、不自动操作集群”的前提下，补充“人工执行方案后的效果验证逻辑”（只读观察指标/状态）  
   - 将验证结果纳入知识沉淀和后续诊断的置信度调整

---

此文档仅描述 **“现在能做什么 / 做不到什么 / 未来准备做什么”**，用于帮助评估当前方案是否符合运维预期，并指导后续迭代优化。***

