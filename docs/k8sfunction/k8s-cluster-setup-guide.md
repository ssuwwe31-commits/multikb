# K8s 集群接入与测试指南

> 本文档说明如何获取 K8s 集群的 API Server 地址，并在诊断平台中配置和测试。

---

## 1. 获取 K8s API Server 地址

### 方法一：通过 kubeconfig 文件（推荐）

如果你有集群的 `kubeconfig` 文件：

```bash
# 查看 kubeconfig 文件中的 API Server 地址
cat ~/.kube/config | grep server

# 或者使用 kubectl 命令
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
```

输出示例：
```
https://192.168.1.100:6443
# 或
https://k8s-api.example.com:6443
```

### 方法二：通过 kubectl 命令

```bash
# 查看当前集群信息
kubectl cluster-info

# 输出示例：
# Kubernetes control plane is running at https://192.168.1.100:6443
# CoreDNS is running at https://192.168.1.100:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

### 方法三：在集群内部通过环境变量

如果你在集群内的 Pod 中：

```bash
# 查看环境变量
env | grep KUBERNETES_SERVICE_HOST
env | grep KUBERNETES_SERVICE_PORT

# API Server 地址通常是：
# https://${KUBERNETES_SERVICE_HOST}:${KUBERNETES_SERVICE_PORT}
```

### 方法四：通过集群管理平台

- **云平台（阿里云、腾讯云、AWS 等）**：在集群管理页面查看“API Server 地址”
- **自建集群**：查看 `kubeadm` 初始化时的输出，或检查 `/etc/kubernetes/admin.conf`

---

## 2. 获取认证凭证

### 方式一：使用 Token（推荐用于服务账号）

#### 1.1 创建新的 ServiceAccount（推荐）

> 下面是**逐步命令**，照抄即可复现，专门解决 `httpx.HTTPStatusError: 403 Forbidden`（访问 `.../namespaces/kube-system/secrets` 被拒绝）的问题。  
> 如需使用其它命名空间，只要把 `default` 换成目标命名空间即可。

**步骤 1：确认当前集群上下文（可选）**

```bash
kubectl config current-context
```

**步骤 2：创建 ServiceAccount（诊断平台使用）**

```bash
kubectl create serviceaccount diagnosis-sa -n default
```

**步骤 3：绑定基础只读权限（view 不含 secrets）**

```bash
kubectl create clusterrolebinding diagnosis-readonly \
  --clusterrole=view \
  --serviceaccount=default:diagnosis-sa
```

**步骤 4：创建可读 secrets 的 ClusterRole**

> **注意**：`EOF` 只是 heredoc 的结束标记，必须单独一行且顶格写，不能把它复制到文件里。如果终端不支持 heredoc，使用下面“写入文件再 apply”或 PowerShell 方案。

```bash
# Linux / macOS（直接 apply）
cat <<'EOF' | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: diagnosis-secrets-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch"]
EOF
```

```bash
# Linux / macOS（写入同目录的 YAML 文件）
cat <<'EOF' > diagnosis-secrets-reader.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: diagnosis-secrets-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch"]
EOF

kubectl apply -f diagnosis-secrets-reader.yaml
```

```powershell
# Windows PowerShell
@"
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: diagnosis-secrets-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch"]
"@ | Set-Content -Path .\diagnosis-secrets-reader.yaml

kubectl apply -f .\diagnosis-secrets-reader.yaml
```

**步骤 5：把 secrets 权限绑定到 diagnosis-sa**

```bash
kubectl create clusterrolebinding diagnosis-secrets-reader-binding \
  --clusterrole=diagnosis-secrets-reader \
  --serviceaccount=default:diagnosis-sa
```

**步骤 6：生成 Token（1.23 及更早版本默认方式）**

```bash
kubectl get secret $(kubectl get sa diagnosis-sa -n default -o jsonpath='{.secrets[0].name}') \
  -n default -o jsonpath='{.data.token}' | base64 -d
```

> 如果你的集群是 1.24+ 并启用了 TokenRequest，可改用：
>
> ```bash
> kubectl -n default create token diagnosis-sa
> ```

**步骤 7：验证 secrets 权限（命名空间按需替换）**

```bash
kubectl auth can-i list secrets -n kube-system \
  --as=system:serviceaccount:default:diagnosis-sa
```

**附加：授予 nodes 资源的只读权限（解决 403 Forbidden: nodes is forbidden）**

> 如果日志出现  
> `User "system:serviceaccount:default:diagnosis-sa" cannot list resource "nodes" ... at the cluster scope`  
> 说明当前 Token 没有集群级别的 `nodes` 访问权限。执行以下命令：

```bash
# 集群级 ClusterRole：允许 get/list/watch nodes
cat <<'EOF' | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: diagnosis-nodes-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
EOF

# 绑定到 diagnosis-sa（default 命名空间，如有需要替换）
kubectl create clusterrolebinding diagnosis-nodes-reader-binding \
  --clusterrole=diagnosis-nodes-reader \
  --serviceaccount=default:diagnosis-sa

# 验证 nodes 权限
kubectl auth can-i list nodes \
  --as=system:serviceaccount:default:diagnosis-sa
```

#### 1.2 查看当前权限

```bash
# 查看 ServiceAccount 的权限
kubectl get clusterrolebindings -o wide | grep my-sa

# 查看某个 ClusterRole 的权限定义
kubectl describe clusterrole view
kubectl describe clusterrole secrets-reader

# 测试权限（需要先获取 Token）
TOKEN="your-token-here"
API_SERVER="https://your-api-server:6443"

# 测试访问 pods
curl -k -H "Authorization: Bearer $TOKEN" "$API_SERVER/api/v1/namespaces/default/pods"

# 测试访问 secrets
curl -k -H "Authorization: Bearer $TOKEN" "$API_SERVER/api/v1/namespaces/default/secrets"
```

### 方式二：使用 kubeconfig 文件

直接使用你的 `~/.kube/config` 文件内容：

```bash
# 查看完整 kubeconfig
cat ~/.kube/config
```

### 方式三：使用现有用户 Token

```bash
# 如果你已经有用户账号，可以获取其 Token
kubectl -n kube-system get secret $(kubectl -n kube-system get sa admin-user -o jsonpath='{.secrets[0].name}') \
  -o jsonpath='{.data.token}' | base64 -d
```

---

## 3. 在诊断平台中配置集群

### 步骤 1：打开集群接入页面

1. 登录诊断平台前端
2. 进入 **运维诊断中心** → **集群接入** Tab

### 步骤 2：填写集群配置

点击 **新增集群** 按钮，填写以下信息：

#### 基本信息
- **集群名称**：给你的集群起个名字，如 `生产集群` 或 `dev-cluster`
- **API Server**：填写步骤 1 中获取的地址，如 `https://192.168.1.100:6443`

#### 认证方式

**选项 A：使用 Token（推荐）**
- **认证方式**：选择 `Token`
- **认证凭证**：粘贴步骤 2 中获取的 Token
- **验证证书**：根据你的集群配置选择（自签名证书需要关闭）

**选项 B：使用 kubeconfig**
- **认证方式**：选择 `Kubeconfig`
- **认证凭证**：粘贴完整的 kubeconfig 文件内容（YAML 格式）

**选项 C：使用证书**
- 如果使用客户端证书认证，填写：
  - **客户端证书**（client_cert）
  - **客户端私钥**（client_key）
  - **CA 证书**（ca_cert，用于验证服务器证书）

#### Prometheus 配置（可选，但推荐）

- **Prometheus 地址**：如 `http://prometheus.example.com:9090`
- **Prometheus 认证**：根据实际情况选择（无认证/Basic/Token）

#### 日志系统配置（可选，但推荐）

- **日志系统**：选择 `ElasticSearch` 或 `Loki`
- **日志入口**：如 `http://elasticsearch.example.com:9200` 或 `http://loki.example.com:3100`
- **日志认证**：根据实际情况配置

#### 启用状态
- **启用**：勾选后集群才会被使用

### 步骤 3：测试连通性

点击 **连通性测试** 按钮，系统会测试：
- ✅ API Server 连接
- ✅ Prometheus 连接（如果配置）
- ✅ 日志系统连接（如果配置）

如果测试通过，会显示绿色状态；如果失败，会显示错误信息。

### 步骤 4：保存配置

点击 **保存** 按钮，集群配置会被保存到数据库。

---

## 4. 开始测试诊断功能

### 测试 1：查看资源快照

1. 进入 **资源快照** Tab
2. 选择刚配置的集群
3. 选择资源类型（如 `pods`）
4. 点击 **查询**，应该能看到集群中的 Pod 列表
5. 点击 **手动同步**，触发资源同步任务

### 测试 2：查询指标

1. 进入 **指标分析** Tab
2. 选择集群
3. 选择指标模板（如 `Pod CPU 使用率`）
4. 选择时间范围
5. 点击 **查询**，应该能看到指标数据

### 测试 3：查询日志

1. 进入 **日志检索** Tab
2. 选择集群
3. 输入查询语句（如 `pod="my-app"` 或 LogQL 查询）
4. 选择时间范围
5. 点击 **查询**，应该能看到日志数据

### 测试 4：发起诊断

1. 进入 **诊断记录** Tab
2. 点击 **手动诊断** 按钮
3. 填写诊断信息：
   - **集群**：选择刚配置的集群
   - **命名空间**：如 `default` 或 `kube-system`
   - **资源类型**：选择 `pods`、`nodes`、`deployments` 等
   - **资源名称**：输入具体的资源名称，如 `my-app-xxx`
4. 点击 **开始诊断**
5. 系统会开始诊断流程，你可以在诊断记录列表中查看进度

### 测试 5：查看诊断结果

1. 在诊断记录列表中，点击 **查看详情**
2. 查看诊断详情页面，包括：
   - 根因分析（5 Why + 证据链）
   - 时间线与影响范围
   - 结构化解决方案
   - 迭代历史
   - 上下文记忆

---

## 5. 常见问题排查

### 问题 1：API Server 连接失败

**可能原因**：
- API Server 地址错误
- 网络不通（防火墙、VPN 等）
- 证书验证失败

**解决方法**：
- 检查 API Server 地址是否正确
- 检查网络连接：`curl -k https://<api-server>:6443/version`
- 如果是自签名证书，关闭“验证证书”选项

### 问题 2：认证失败

**可能原因**：
- Token 过期或无效
- kubeconfig 格式错误
- 权限不足

**解决方法**：
- 重新生成 Token
- 检查 kubeconfig 文件格式
- 确保 ServiceAccount 有足够的权限（至少需要 `view` ClusterRole）

### 问题 3：Prometheus 连接失败

**可能原因**：
- Prometheus 地址错误
- 认证信息错误
- Prometheus 未配置 Service Discovery

**解决方法**：
- 检查 Prometheus 地址和端口
- 检查认证信息（用户名/密码或 Token）
- 确保 Prometheus 已配置 `kubernetes_sd_config` 自动发现

### 问题 4：日志系统连接失败

**可能原因**：
- 日志系统地址错误
- 认证信息错误
- 日志系统未配置或未运行

**解决方法**：
- 检查日志系统地址和端口
- 检查认证信息
- 确保日志系统正常运行：`curl http://<log-endpoint>/health`

### 问题 5：资源同步失败

**可能原因**：
- API Server 权限不足
- 资源类型不存在
- 命名空间不存在

**解决方法**：
- 检查 ServiceAccount 权限（需要 `list` 和 `get` 权限）
- 检查资源类型是否正确（如 `pods` 不是 `pod`）
- 检查命名空间是否存在

---

## 6. 权限要求

### 6.1 最小权限要求

为了正常使用诊断功能，建议为 ServiceAccount 授予以下权限：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: diagnosis-readonly
rules:
- apiGroups: [""]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: diagnosis-readonly-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: diagnosis-readonly
subjects:
- kind: ServiceAccount
  name: diagnosis-sa
  namespace: default
```

### 6.2 授予 secrets 资源访问权限

**重要提示**：`view` ClusterRole 默认**不包含** `secrets` 资源的访问权限（出于安全考虑）。如果需要同步 secrets 资源，需要额外授予权限：

```yaml
# 创建 secrets 读取权限
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secrets-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch"]
---
# 绑定到 ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: diagnosis-secrets-reader-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: secrets-reader
subjects:
- kind: ServiceAccount
  name: diagnosis-sa
  namespace: default
```

**快速命令**（为已存在的 ServiceAccount 授予 secrets 权限）：

```bash
# 创建 ClusterRole
kubectl create clusterrole secrets-reader \
  --verb=get,list,watch \
  --resource=secrets

# 创建 ClusterRoleBinding（替换为你的 ServiceAccount 名称和命名空间）
kubectl create clusterrolebinding my-sa-secrets-reader \
  --clusterrole=secrets-reader \
  --serviceaccount=<namespace>:<serviceaccount-name>

# 示例：如果 ServiceAccount 名称是 my-sa，命名空间是 default
kubectl create clusterrolebinding my-sa-secrets-reader \
  --clusterrole=secrets-reader \
  --serviceaccount=default:my-sa
```

### 6.3 权限说明

| 资源类型 | 所需权限 | 默认 view 角色 | 说明 |
|---------|---------|---------------|------|
| pods | get, list, watch | ✅ 包含 | 基础资源，默认可访问 |
| deployments | get, list, watch | ✅ 包含 | 基础资源，默认可访问 |
| configmaps | get, list, watch | ✅ 包含 | 基础资源，默认可访问 |
| secrets | get, list, watch | ❌ **不包含** | 敏感资源，需要额外授权 |
| nodes | get, list, watch | ✅ 包含 | 集群级别资源 |

**建议**：
- 如果不需要同步 secrets，可以不授予 secrets 权限（系统会自动跳过，不影响其他资源同步）
- 如果需要完整的诊断能力，建议授予 secrets 权限
- 生产环境请根据安全策略决定是否授予 secrets 权限

---

## 7. 快速测试脚本

如果你想快速测试 API Server 连接，可以使用以下脚本：

```bash
#!/bin/bash

# 配置变量
API_SERVER="https://192.168.1.100:6443"
TOKEN="your-token-here"

# 测试连接
echo "测试 API Server 连接..."
curl -k -H "Authorization: Bearer $TOKEN" "$API_SERVER/version"

# 测试获取 Pod 列表
echo -e "\n\n测试获取 Pod 列表..."
curl -k -H "Authorization: Bearer $TOKEN" "$API_SERVER/api/v1/namespaces/default/pods"

# 测试获取 Node 列表
echo -e "\n\n测试获取 Node 列表..."
curl -k -H "Authorization: Bearer $TOKEN" "$API_SERVER/api/v1/nodes"
```

如果以上命令都能正常返回数据，说明配置正确。

---

## 8. 下一步

配置完成后，你可以：

1. **查看资源快照**：了解集群中所有资源的当前状态
2. **查询指标和日志**：分析集群的运行情况
3. **发起诊断**：对异常资源进行自动诊断
4. **查看诊断结果**：获取根因分析和解决方案

如有问题，请查看诊断记录中的错误信息，或联系运维团队。

