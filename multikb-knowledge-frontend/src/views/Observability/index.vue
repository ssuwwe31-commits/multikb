<template>
  <div class="observability-page">
    <el-card class="observability-card" v-loading="pageLoading">
      <template #header>
        <div class="card-header">
          <div class="title">
            <el-icon><Monitor /></el-icon>
            <span>运维诊断中心</span>
          </div>
          <el-button
            v-if="activeTab === 'clusters'"
            type="primary"
            @click="openClusterDialog()"
          >
            新增集群
          </el-button>
          <el-button
            v-else-if="activeTab === 'diagnosis'"
            type="primary"
            plain
            @click="openManualDiagnosis"
          >
            手动诊断
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="集群接入" name="clusters">
          <div class="tab-section">
            <el-table :data="clusters" size="default" stripe style="width: 100%">
              <el-table-column prop="name" label="集群名称" width="120" fixed="left">
                <template #default="{ row }">
                  <div class="cluster-name">
                    <span class="cluster-name-text">{{ row.name }}</span>
                    <el-tag
                      v-if="row.is_active"
                      size="small"
                      type="success"
                      effect="light"
                    >
                      启用
                    </el-tag>
                    <el-tag
                      v-else
                      size="small"
                      type="info"
                    >
                      停用
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="集群配置" min-width="400">
                <template #default="{ row }">
                  <div class="cluster-config">
                    <div class="config-row">
                      <span class="config-label">API:</span>
                      <span class="api-server-text">{{ row.api_server }}</span>
                    </div>
                    <div class="config-row">
                      <span class="config-label">Prom:</span>
                      <el-tag v-if="row.prometheus_url" type="success" size="small" effect="plain">已配置</el-tag>
                      <el-tag v-else type="info" size="small" effect="plain">未配置</el-tag>
                    </div>
                    <div class="config-row">
                      <span class="config-label">日志:</span>
                      <el-tag v-if="row.log_system" type="success" size="small" effect="plain">{{ row.log_system }}</el-tag>
                      <el-tag v-else type="info" size="small" effect="plain">未配置</el-tag>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="健康状态" min-width="160">
                <template #default="{ row }">
                  <div class="health-status-list">
                    <div class="health-item">
                      <span class="health-label">API:</span>
                      <el-tag
                        :type="healthStatusTagType(row.last_health_status)"
                        effect="dark"
                        size="small"
                        class="health-tag"
                      >
                        {{ formatStatusText(row.last_health_status) || '未知' }}
                      </el-tag>
                    </div>
                    <div class="health-item">
                      <span class="health-label">Prom:</span>
                      <el-tag
                        v-if="row.prometheus_url"
                        :type="healthStatusTagType(row.last_health_status)"
                        effect="dark"
                        size="small"
                        class="health-tag"
                      >
                        {{ formatStatusText(row.last_health_status) || '未知' }}
                      </el-tag>
                      <span v-else class="health-empty">-</span>
                    </div>
                    <div class="health-item">
                      <span class="health-label">日志:</span>
                      <el-tag
                        v-if="row.log_system"
                        :type="healthStatusTagType(row.last_health_status)"
                        effect="dark"
                        size="small"
                        class="health-tag"
                      >
                        {{ formatStatusText(row.last_health_status) || '未知' }}
                      </el-tag>
                      <span v-else class="health-empty">-</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180" fixed="right" align="center">
                <template #default="{ row }">
                  <div class="actions">
                    <el-button size="small" type="primary" plain @click="handleTestConnectivity(row)">
                      测试
                    </el-button>
                    <el-button size="small" @click="handleHealthCheck(row)">
                      检查
                    </el-button>
                    <el-dropdown trigger="click">
                      <el-button size="small" circle>
                        <el-icon><MoreFilled /></el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item @click="openClusterDialog(row)">
                            <el-icon><Edit /></el-icon>
                            编辑配置
                          </el-dropdown-item>
                          <el-dropdown-item @click="handleDeleteCluster(row)" divided type="danger">
                            <el-icon><Delete /></el-icon>
                            删除集群
                          </el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <el-empty
              v-if="!pageLoading && clusters.length === 0"
              description="暂无集群数据，请点击上方「新增集群」按钮添加集群"
              :image-size="120"
            />

            <div class="pagination-container" v-if="clusterPagination.total > 0">
              <el-pagination
                layout="prev, pager, next"
                :page-size="clusterPagination.size"
                :total="clusterPagination.total"
                v-model:current-page="clusterPagination.page"
                @current-change="loadClusters"
              />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="资源快照" name="resources">
          <div class="tab-section">
            <el-form
              :inline="true"
              :model="resourceFilters"
              class="filter-form"
            >
              <el-form-item label="集群">
                <el-select
                  v-model="resourceFilters.clusterId"
                  placeholder="选择集群"
                  @change="loadResources(true)"
                  style="width: 200px"
                >
                  <el-option
                    v-for="cluster in clusters"
                    :key="cluster.id"
                    :label="cluster.name"
                    :value="cluster.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="资源类型">
                <el-select
                  v-model="resourceFilters.resourceType"
                  placeholder="选择资源类型"
                  @change="loadResources(true)"
                  style="width: 200px"
                >
                  <el-option
                    v-for="item in resourceTypeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="命名空间">
                <el-input
                  v-model="resourceFilters.namespace"
                  placeholder="默认 default"
                  style="width: 180px"
                  clearable
                  @keyup.enter="loadResources(true)"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="loadResources(true)">
                  查询
                </el-button>
                <el-button @click="handleManualSync">
                  手动同步
                </el-button>
              </el-form-item>
            </el-form>

            <el-table :data="resourceSnapshots" v-loading="resourceLoading" size="large">
              <el-table-column prop="resource_name" label="资源名称" min-width="160" />
              <el-table-column prop="resource_uid" label="UID" min-width="220" show-overflow-tooltip />
              <el-table-column prop="resource_type" label="类型" width="120" />
              <el-table-column prop="namespace" label="命名空间" width="140" />
              <el-table-column prop="resource_version" label="版本" width="160" show-overflow-tooltip />
              <el-table-column label="最后更新" min-width="160">
                <template #default="{ row }">
                  {{ formatDateTime(row.updated_at) }}
                </template>
              </el-table-column>
              <el-table-column type="expand" width="70">
                <template #default="{ row }">
                  <div class="snapshot-expand">
                    <el-descriptions border :column="1" size="small">
                      <el-descriptions-item label="标签">
                        <el-tag
                          v-for="(value, key) in row.labels"
                          :key="key"
                          size="small"
                          class="tag"
                        >
                          {{ key }}={{ value }}
                        </el-tag>
                        <span v-if="!row.labels" class="text-muted">-</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="状态">
                        <pre class="json-preview">{{ stringify(row.status) }}</pre>
                      </el-descriptions-item>
                      <el-descriptions-item label="规格">
                        <pre class="json-preview">{{ stringify(row.spec) }}</pre>
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-container">
              <el-pagination
                layout="prev, pager, next"
                :page-size="resourceFilters.size"
                :total="resourcePagination.total"
                v-model:current-page="resourceFilters.page"
                @current-change="handleResourcePageChange"
              />
            </div>

            <el-card v-if="recentSyncEvents.length" class="event-card" shadow="never">
              <template #header>
                <div class="event-header">
                  <span>最近同步变更</span>
                  <el-tag type="info">{{ recentSyncEvents.length }}</el-tag>
                </div>
              </template>
              <el-timeline>
                <el-timeline-item
                  v-for="(evt, index) in recentSyncEvents"
                  :key="index"
                  :timestamp="evt.timestamp"
                  :type="eventTagType(evt.type)"
                >
                  <div class="event-item">
                    <el-tag size="small" :type="eventTagType(evt.type)">
                      {{ evt.type.toUpperCase() }}
                    </el-tag>
                    <span class="event-text">{{ evt.message }}</span>
                    <pre v-if="evt.diff" class="json-preview">{{ stringify(evt.diff) }}</pre>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="指标分析" name="metrics">
          <div class="tab-section">
            <el-form
              :inline="true"
              :model="metricsForm"
              class="filter-form"
            >
              <el-form-item label="集群">
                <el-select
                  v-model="metricsForm.cluster_id"
                  placeholder="选择集群"
                  style="width: 200px"
                >
                  <el-option
                    v-for="cluster in clusters"
                    :key="cluster.id"
                    :label="cluster.name"
                    :value="cluster.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="指标模板">
                <el-select
                  v-model="metricsForm.template_id"
                  placeholder="选择模板或自定义 PromQL"
                  style="width: 220px"
                  clearable
                  @change="handleTemplateChange"
                >
                  <el-option
                    v-for="item in metricTemplateOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="needsNamespace" label="命名空间">
                <el-select
                  v-model="metricsForm.context.namespace"
                  placeholder="选择命名空间"
                  style="width: 180px"
                  filterable
                  :loading="namespaceLoading"
                  @change="handleNamespaceChange"
                >
                  <el-option
                    v-for="ns in namespaces"
                    :key="ns"
                    :label="ns"
                    :value="ns"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="needsPod" label="Pod名称">
                <el-select
                  v-model="metricsForm.context.pod"
                  placeholder="选择Pod"
                  style="width: 220px"
                  filterable
                  :loading="podLoading"
                  :disabled="!metricsForm.context.namespace"
                >
                  <el-option
                    v-for="pod in pods"
                    :key="pod"
                    :label="pod"
                    :value="pod"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="needsWindow" label="时间窗口">
                <el-input
                  v-model="metricsForm.context.window"
                  placeholder="如: 5m"
                  style="width: 100px"
                />
              </el-form-item>
              <el-form-item label="时间范围">
                <el-date-picker
                  v-model="metricsForm.range"
                  type="datetimerange"
                  range-separator="至"
                  start-placeholder="开始时间"
                  end-placeholder="结束时间"
                  :default-time="defaultTimeRange"
                />
              </el-form-item>
              <el-form-item label="PromQL">
                <el-input
                  v-model="metricsForm.promql"
                  placeholder="自定义 PromQL，留空使用模板"
                  style="width: 320px"
                  clearable
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleQueryMetrics">
                  查询
                </el-button>
                <el-button @click="resetMetricsForm">
                  重置
                </el-button>
              </el-form-item>
            </el-form>

            <div v-if="metricsResult" class="metrics-result">
              <el-alert
                :title="`查询状态：${metricsResult.status}`"
                type="success"
                show-icon
                style="margin-bottom: 16px"
              />
              
              <!-- 图表展示 -->
              <el-card v-if="chartOptions" shadow="never" style="margin-bottom: 16px">
                <template #header>
                  <div class="event-header">
                    <span>指标趋势图</span>
                  </div>
                </template>
                <v-chart
                  :option="chartOptions"
                  :autoresize="true"
                  style="height: 400px; width: 100%"
                />
              </el-card>

              <!-- 数据表格 -->
              <el-table :data="metricsSeries" border style="margin-bottom: 16px">
                <el-table-column prop="series" label="序列" min-width="220" />
                <el-table-column prop="latest" label="最新值" width="140" />
                <el-table-column prop="average" label="平均值" width="140" />
                <el-table-column label="标签" min-width="200">
                  <template #default="{ row }">
                    <el-tag
                      v-for="(value, key) in row.labels"
                      :key="key"
                      size="small"
                      class="tag"
                    >
                      {{ key }}={{ value }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>

              <!-- 原始数据 -->
              <el-card class="json-card" shadow="never">
                <template #header>
                  <div class="event-header">
                    <span>原始响应</span>
                    <el-button size="small" text @click="copyRaw(metricsResult.data)">复制 JSON</el-button>
                  </div>
                </template>
                <pre class="json-preview">{{ stringify(metricsResult.data) }}</pre>
              </el-card>
            </div>
            <el-empty v-else description="请选择查询条件并点击查询" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="日志检索" name="logs">
          <div class="tab-section">
            <el-form
              :inline="true"
              :model="logForm"
              class="filter-form"
            >
              <el-form-item label="集群">
                <el-select
                  v-model="logForm.cluster_id"
                  placeholder="选择集群"
                  style="width: 200px"
                >
                  <el-option
                    v-for="cluster in clusters"
                    :key="cluster.id"
                    :label="cluster.name"
                    :value="cluster.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="查询语句">
                <el-input
                  v-model="logForm.query"
                  placeholder='如 pod="my-app" 或 Loki LogQL'
                  style="width: 320px"
                  clearable
                />
              </el-form-item>
              <el-form-item label="时间范围">
                <el-date-picker
                  v-model="logForm.range"
                  type="datetimerange"
                  range-separator="至"
                  start-placeholder="开始时间"
                  end-placeholder="结束时间"
                  :default-time="defaultTimeRange"
                />
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="logForm.highlight" label="高亮关键字" />
                <el-checkbox v-model="logForm.stats" label="输出统计" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleQueryLogs">
                  查询
                </el-button>
                <el-button @click="resetLogForm">
                  重置
                </el-button>
              </el-form-item>
            </el-form>

            <el-row :gutter="16" v-if="logResult?.stats">
              <el-col :span="12">
                <el-card shadow="never">
                  <template #header>
                    <div class="event-header">
                      <span>等级分布</span>
                    </div>
                  </template>
                  <el-tag
                    v-for="(count, level) in logResult.stats.level_counts"
                    :key="level"
                    :type="logLevelTagType(level)"
                    class="tag"
                  >
                    {{ level }}：{{ count }}
                  </el-tag>
                </el-card>
              </el-col>
            </el-row>

            <el-table
              v-if="logResult"
              :data="logResult.results"
              size="large"
              class="log-table"
            >
              <el-table-column prop="timestamp" label="时间" width="200">
                <template #default="{ row }">
                  {{ formatDateTime(row.timestamp) }}
                </template>
              </el-table-column>
              <el-table-column prop="severity" label="级别" width="120">
                <template #default="{ row }">
                  <el-tag :type="logLevelTagType(row.severity)">
                    {{ row.severity || 'unknown' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="message" label="日志内容" min-width="360">
                <template #default="{ row }">
                  <div v-if="row.highlight" v-html="renderHighlight(row.highlight)"></div>
                  <div v-else class="log-text">{{ row.message }}</div>
                </template>
              </el-table-column>
              <el-table-column label="标签" min-width="200">
                <template #default="{ row }">
                  <el-tag
                    v-for="(value, key) in row.labels"
                    :key="key"
                    size="small"
                    class="tag"
                  >
                    {{ key }}={{ value }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>

            <el-pagination
              v-if="logResult"
              class="pagination-container"
              layout="prev, pager, next"
              :page-size="logForm.page_size"
              :total="logResult.pagination.total || 0"
              v-model:current-page="logForm.page"
              @current-change="handleQueryLogs"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="诊断记录" name="diagnosis">
          <div class="tab-section">
            <el-table :data="diagnosisList" v-loading="diagnosisLoading" size="large">
              <el-table-column prop="resource_name" label="资源" min-width="200" align="left">
                <template #default="{ row }">
                  {{ row.namespace || 'default' }} / {{ row.resource_name }}
                </template>
              </el-table-column>
              <el-table-column prop="resource_type" label="资源类型" width="120" align="center">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.resource_type || 'pods' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="diagnosisStatusTag(row.status)">
                    {{ formatDiagnoseStatus(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="confidence" label="置信度" width="120" align="center">
                <template #default="{ row }">
                  <el-tag
                    v-if="row.confidence != null"
                    :type="row.confidence > 0.7 ? 'success' : row.confidence > 0.4 ? 'warning' : 'danger'"
                    size="small"
                  >
                    {{ Math.round((row.confidence || 0) * 100) }}%
                  </el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="summary" label="摘要" min-width="260" show-overflow-tooltip align="left" />
              <el-table-column label="知识来源" width="140" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.knowledge_source" type="info" size="small">{{ sourceText(row.knowledge_source) }}</el-tag>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column label="时间" min-width="200" align="left">
                <template #default="{ row }">
                  <div class="has-sub-text">
                    <div>{{ formatDateTime(row.started_at) }}</div>
                    <div class="sub-text">{{ formatDateTime(row.completed_at) }}</div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button size="small" @click="openDiagnosisDetail(row)">
                    查看详情
                  </el-button>
                  <el-button
                    size="small"
                    type="danger"
                    plain
                    @click="handleDeleteDiagnosis(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-container">
              <el-pagination
                layout="prev, pager, next"
                :page-size="diagnosisPagination.size"
                :total="diagnosisPagination.total"
                v-model:current-page="diagnosisPagination.page"
                @current-change="loadDiagnosis"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 集群配置对话框 -->
    <el-dialog
      v-model="clusterDialog.visible"
      :title="clusterDialog.editing ? '编辑集群' : '新增集群'"
      width="640px"
    >
      <el-form ref="clusterFormRef" :model="clusterDialog.form" :rules="clusterRules" label-width="110px">
        <el-form-item label="集群名称" prop="name">
          <el-input v-model="clusterDialog.form.name" placeholder="唯一名称" />
        </el-form-item>
        <el-form-item label="API Server" prop="api_server">
          <el-input v-model="clusterDialog.form.api_server" placeholder="https://k8s-api.example.com" />
        </el-form-item>
        <el-form-item label="认证方式" prop="auth_type">
          <el-select v-model="clusterDialog.form.auth_type">
            <el-option label="Token" value="token" />
            <el-option label="Basic" value="basic" />
            <el-option label="Kubeconfig" value="kubeconfig" />
          </el-select>
        </el-form-item>
        <el-form-item label="认证凭证" prop="auth_token">
          <el-input
            v-if="clusterDialog.form.auth_type !== 'kubeconfig'"
            v-model="clusterDialog.form.auth_token"
            type="textarea"
            :rows="3"
            placeholder="Bearer Token / Authorization Header"
          />
          <el-input
            v-else
            v-model="clusterDialog.form.kubeconfig"
            type="textarea"
            :rows="6"
            placeholder="kubeconfig YAML"
          />
        </el-form-item>
        <el-form-item label="验证证书">
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-switch v-model="clusterDialog.form.verify_ssl" />
            <span style="font-size: 12px; color: rgba(255, 255, 255, 0.6);">
              {{ clusterDialog.form.verify_ssl ? '启用（推荐）' : '禁用（自签名证书时使用）' }}
            </span>
          </div>
        </el-form-item>
        <el-form-item label="客户端证书" v-if="clusterDialog.form.auth_type === 'kubeconfig' || clusterDialog.form.verify_ssl">
          <el-input
            v-model="clusterDialog.form.client_cert"
            type="textarea"
            :rows="4"
            placeholder="客户端证书（PEM 格式）"
          />
        </el-form-item>
        <el-form-item label="客户端私钥" v-if="clusterDialog.form.auth_type === 'kubeconfig' || clusterDialog.form.verify_ssl">
          <el-input
            v-model="clusterDialog.form.client_key"
            type="textarea"
            :rows="4"
            placeholder="客户端私钥（PEM 格式）"
          />
        </el-form-item>
        <el-form-item label="CA 证书" v-if="clusterDialog.form.verify_ssl">
          <el-input
            v-model="clusterDialog.form.ca_cert"
            type="textarea"
            :rows="4"
            placeholder="CA 证书（PEM 格式，用于验证服务器证书）"
          />
        </el-form-item>
        <el-form-item label="Prometheus 地址">
          <el-input v-model="clusterDialog.form.prometheus_url" placeholder="http://prometheus.example.com" />
        </el-form-item>
        <el-form-item label="Prometheus 认证">
          <el-select v-model="clusterDialog.form.prometheus_auth_type">
            <el-option v-for="option in PROM_AUTH_OPTIONS" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="clusterDialog.form.prometheus_auth_type === 'basic'" label="Prometheus 用户">
          <el-input v-model="clusterDialog.form.prometheus_username" placeholder="用户名" />
        </el-form-item>
        <el-form-item v-if="clusterDialog.form.prometheus_auth_type === 'basic'" label="Prometheus 密码">
          <el-input
            v-model="clusterDialog.form.prometheus_password"
            type="password"
            placeholder="密码"
            show-password
          />
        </el-form-item>
        <el-form-item v-else-if="clusterDialog.form.prometheus_auth_type === 'token'" label="Prometheus Token">
          <el-input
            v-model="clusterDialog.form.prometheus_password"
            type="textarea"
            :rows="2"
            placeholder="请输入 Token"
          />
        </el-form-item>
        <el-form-item label="日志系统">
          <el-select v-model="clusterDialog.form.log_system" clearable placeholder="选择日志系统">
            <el-option label="ElasticSearch" value="elk" />
            <el-option label="Loki" value="loki" />
            <el-option label="其他" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="日志入口">
          <el-input v-model="clusterDialog.form.log_endpoint" placeholder="http://logging.example.com" />
        </el-form-item>
        <template v-if="clusterDialog.form.log_system">
          <el-form-item label="日志认证">
            <el-select v-model="clusterDialog.form.log_auth_type">
              <el-option v-for="option in LOG_AUTH_OPTIONS" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="clusterDialog.form.log_auth_type === 'basic'" label="日志用户名">
            <el-input v-model="clusterDialog.form.log_username" placeholder="用户名" />
          </el-form-item>
          <el-form-item v-if="clusterDialog.form.log_auth_type === 'basic'" label="日志密码">
            <el-input
              v-model="clusterDialog.form.log_password"
              type="password"
              placeholder="密码"
              show-password
            />
          </el-form-item>
          <el-form-item v-else-if="clusterDialog.form.log_auth_type === 'token'" label="日志 Token">
            <el-input
              v-model="clusterDialog.form.log_password"
              type="textarea"
              :rows="2"
              placeholder="请输入 Token"
            />
          </el-form-item>
        </template>
        <el-form-item label="启用">
          <el-switch v-model="clusterDialog.form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="clusterDialog.visible = false">取 消</el-button>
        <el-button type="primary" @click="submitClusterForm">保 存</el-button>
      </template>
    </el-dialog>

    <!-- 连通性测试 -->
    <el-dialog v-model="connectivityDialog.visible" title="连通性测试结果" width="600px">
      <el-descriptions border :column="1" size="default">
        <el-descriptions-item label="API Server">
          <div class="health-result">
            <el-tag 
              :type="healthStatusTagType(connectivityDialog.result?.api_server?.status)" 
              size="default"
              class="health-status-tag"
            >
              {{ formatStatusText(connectivityDialog.result?.api_server?.status) || '未知' }}
            </el-tag>
            <div class="health-message">
              {{ connectivityDialog.result?.api_server?.message || '未测试' }}
            </div>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="Prometheus" v-if="connectivityDialog.result?.prometheus">
          <div class="health-result">
            <el-tag 
              :type="healthStatusTagType(connectivityDialog.result?.prometheus?.status)" 
              size="default"
              class="health-status-tag"
            >
              {{ formatStatusText(connectivityDialog.result?.prometheus?.status) || '未知' }}
            </el-tag>
            <div class="health-message">
              {{ connectivityDialog.result?.prometheus?.message || '未配置或未测试' }}
            </div>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="日志系统" v-if="connectivityDialog.result?.logging">
          <div class="health-result">
            <el-tag 
              :type="healthStatusTagType(connectivityDialog.result?.logging?.status)" 
              size="default"
              class="health-status-tag"
            >
              {{ formatStatusText(connectivityDialog.result?.logging?.status) || '未知' }}
            </el-tag>
            <div class="health-message">
              {{ connectivityDialog.result?.logging?.message || '未配置或未测试' }}
            </div>
          </div>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="connectivityDialog.visible = false">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 诊断详情 -->
    <el-drawer
      v-model="diagnosisDrawer.visible"
      size="50%"
      destroy-on-close
      append-to-body
    >
      <template #title>
        <div class="drawer-header">
          <span>{{ `诊断详情 - ${diagnosisDrawer.record?.resource_name || ''}` }}</span>
        </div>
      </template>
      <div v-if="diagnosisDrawer.record" class="diagnosis-detail">
        <div class="diagnosis-hero">
          <div class="hero-main">
            <div class="hero-tag">{{ diagnosisDrawer.record.resource_type?.toUpperCase() || 'RESOURCE' }}</div>
            <h2>{{ diagnosisDrawer.record.resource_name || '未命名资源' }}</h2>
            <p class="hero-meta">
              最近更新：{{ diagnosisUpdatedAt || '-' }}
              <span class="meta-divider">•</span>
              触发来源：{{ diagnosisDrawer.record.trigger_source || '-' }}
            </p>
          </div>
          <div class="hero-stats">
            <div class="hero-stat-card">
              <span class="stat-label">命名空间</span>
              <span class="stat-value">{{ diagnosisDrawer.record.namespace || 'default' }}</span>
            </div>
            <div class="hero-stat-card">
              <span class="stat-label">状态</span>
              <el-tag :type="diagnosisStatusTag(diagnosisDrawer.record.status)">
                {{ formatDiagnoseStatus(diagnosisDrawer.record.status) }}
              </el-tag>
            </div>
            <div class="hero-stat-card">
              <span class="stat-label">知识来源</span>
              <span class="stat-value">{{ diagnosisDrawer.record.knowledge_source ? sourceText(diagnosisDrawer.record.knowledge_source) : '知识库' }}</span>
            </div>
            <div class="hero-stat-card confidence-card">
              <span class="stat-label">置信度</span>
              <div v-if="diagnosisConfidencePercent !== null" class="confidence-meter">
                <el-progress
                  type="circle"
                  :width="90"
                  :percentage="diagnosisConfidencePercent"
                  :status="diagnosisConfidenceStatus"
                />
              </div>
              <span v-else class="stat-value">-</span>
            </div>
          </div>
        </div>

        <div class="diagnosis-layout">
          <div class="column column-primary">
        <el-card v-if="diagnosisDrawer.record.summary" shadow="never" class="json-card">
          <template #header>
            <span>摘要</span>
          </template>
          <p class="summary-text">{{ diagnosisDrawer.record.summary }}</p>
        </el-card>

        <el-card v-if="iterationTimeline.length > 0 || iterationLoading" shadow="never" class="json-card">
          <template #header>
            <div class="event-header">
              <span>迭代历史</span>
            </div>
          </template>
          <div v-loading="iterationLoading">
            <el-timeline v-if="iterationTimeline.length">
              <el-timeline-item
                v-for="item in iterationTimeline"
                :key="item.id"
                :timestamp="formatDateTime(item.created_at)"
                :type="diagnosisStatusTag(item.status)"
              >
                <div class="event-item">
                  <el-tag size="small" :type="diagnosisStatusTag(item.status)">
                    {{ item.stage || `迭代 ${item.iteration_no}` }}
                  </el-tag>
                  <div class="event-text">{{ item.reasoning_summary || '无摘要' }}</div>
                  <pre v-if="item.action_result" class="json-preview">{{ stringify(item.action_result) }}</pre>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无迭代数据" />
          </div>
        </el-card>

        <el-card v-if="memoryTimeline.length > 0 || memoryLoading" shadow="never" class="json-card">
          <template #header>
            <div class="event-header">
              <span>上下文记忆</span>
            </div>
          </template>
          <div v-loading="memoryLoading">
            <el-timeline v-if="memoryTimeline.length">
              <el-timeline-item
                v-for="memory in memoryTimeline"
                :key="memory.id"
                :timestamp="formatDateTime(memory.created_at)"
                :type="memory.memory_type === 'error' ? 'danger' : 'info'"
              >
                <div class="event-item">
                  <el-tag size="small" type="info">
                    {{ memory.memory_type }}{{ memory.iteration_no ? ` #${memory.iteration_no}` : '' }}
                  </el-tag>
                  <div class="event-text">{{ memory.summary || '无摘要' }}</div>
                  <pre v-if="memory.content" class="json-preview">{{ stringify(memory.content) }}</pre>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无上下文记忆" />
          </div>
        </el-card>

        <el-card v-if="diagnosisDrawer.record.events && diagnosisDrawer.record.events.length > 0" shadow="never" class="json-card">
          <template #header>
            <span>诊断事件</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(event, index) in diagnosisDrawer.record.events"
              :key="index"
              :timestamp="formatDateTime(event.timestamp)"
              :type="eventStatusType(event.status)"
            >
              <div class="event-item">
                <el-tag :type="eventStatusType(event.status)" size="small">{{ event.stage }}</el-tag>
                <div class="event-text">{{ event.message }}</div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>

          </div>
          <div class="column column-secondary">

        <!-- 根因分析 -->
        <el-card v-if="diagnosisDrawer.record && (getRootCauseAnalysis(diagnosisDrawer.record)?.root_cause || getRootCauseAnalysis(diagnosisDrawer.record)?.root_cause_analysis)" shadow="never" class="json-card">
          <template #header>
            <span>根因分析</span>
          </template>
          <div class="scrollable-card-body">
            <div v-if="getRootCauseAnalysis(diagnosisDrawer.record)?.root_cause" class="root-cause-section">
              <h4>根因结论</h4>
              <p class="root-cause-text">{{ getRootCauseAnalysis(diagnosisDrawer.record).root_cause }}</p>
            </div>
            <div v-if="getRootCauseAnalysis(diagnosisDrawer.record)?.root_cause_analysis" class="why-analysis-section">
              <h4>5 Why 分析</h4>
              <el-steps direction="vertical" :active="5">
                <el-step
                  v-for="(why, index) in getWhySteps(getRootCauseAnalysis(diagnosisDrawer.record)?.root_cause_analysis)"
                  :key="index"
                  :title="'问题' + (index + 1)"
                  :description="why"
                />
              </el-steps>
            </div>
          </div>
        </el-card>

        <!-- 证据链 - 独立卡片展示 -->
        <template v-if="diagnosisDrawer.record && Object.keys(getAllEvidenceChain(diagnosisDrawer.record)).length > 0">
          <el-card
            v-for="(value, key) in getAllEvidenceChain(diagnosisDrawer.record)"
            :key="key"
            shadow="never"
            class="json-card evidence-card"
            :class="`evidence-card-${key.toLowerCase()}`"
          >
            <template #header>
              <div class="evidence-card-header">
                <el-icon :class="`evidence-icon-${key.toLowerCase()}`">
                  <component :is="getEvidenceIcon(key)" />
                </el-icon>
                <span class="evidence-card-title">{{ getEvidenceTitle(key) }}</span>
              </div>
            </template>
            
            <!-- Logs 展示 -->
            <template v-if="key.toLowerCase() === 'logs'">
              <div v-if="Array.isArray(value) && value.length > 0" class="evidence-logs">
                <div
                  v-for="(item, idx) in value"
                  :key="idx"
                  class="evidence-log-item"
                  :class="{ 'is-error': isErrorLog(item) }"
                >
                  <el-icon class="log-icon">
                    <component :is="isErrorLog(item) ? 'WarningFilled' : 'InfoFilled'" />
                  </el-icon>
                  <span class="log-text">{{ typeof item === 'string' ? item : stringify(item) }}</span>
                </div>
              </div>
              <el-empty v-else description="暂无日志数据" :image-size="80" />
            </template>
            
            <!-- Config 展示 -->
            <template v-else-if="key.toLowerCase() === 'config'">
              <div v-if="value && typeof value === 'object' && Object.keys(value).length > 0" class="config-container">
                <el-descriptions 
                  :column="1" 
                  size="default" 
                  border 
                  class="config-descriptions"
                  ref="configDescriptionsRef"
                >
                  <el-descriptions-item
                    v-for="(configValue, configKey) in value"
                    :key="configKey"
                    :label="configKey"
                    class="config-item-row"
                  >
                    <span class="config-value">{{ formatConfigValue(configValue) }}</span>
                  </el-descriptions-item>
                </el-descriptions>
              </div>
              <el-empty v-else description="暂无配置数据" :image-size="80" />
            </template>
            
            <!-- Events 展示 -->
            <template v-else-if="key.toLowerCase() === 'events'">
              <div v-if="Array.isArray(value) && value.length > 0" class="evidence-events">
                <el-alert
                  v-for="(item, idx) in value"
                  :key="idx"
                  :type="getEventAlertType(item)"
                  :closable="false"
                  class="evidence-event-alert"
                  :class="getEventAlertClass(item)"
                >
                  <template #icon>
                    <el-icon class="event-icon">
                      <component :is="getEventIcon(item)" />
                    </el-icon>
                  </template>
                  <div class="event-content">
                    <div class="event-text">{{ typeof item === 'string' ? item : (item.message || stringify(item)) }}</div>
                    <div v-if="item && typeof item === 'object' && item.timestamp" class="event-time">
                      {{ formatDateTime(item.timestamp) }}
                    </div>
                  </div>
                </el-alert>
              </div>
              <el-empty v-else description="暂无事件数据" :image-size="80" />
            </template>
            
            <!-- Metrics 展示 -->
            <template v-else-if="key.toLowerCase() === 'metrics'">
              <div v-if="value && typeof value === 'object' && Object.keys(value).length > 0" class="evidence-metrics">
                <div
                  v-for="(metricValue, metricKey) in value"
                  :key="metricKey"
                  class="evidence-metric-item"
                >
                  <div class="metric-label">{{ metricKey }}</div>
                  <div class="metric-value" :class="getMetricValueClass(metricValue)">
                    {{ formatMetricValue(metricValue) }}
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无指标数据" :image-size="80" />
            </template>
            
            <!-- 默认展示 -->
            <template v-else>
              <template v-if="Array.isArray(value) && value.length > 0">
                <div class="evidence-list">
                  <div
                    v-for="(item, idx) in value"
                    :key="idx"
                    class="evidence-list-item"
                  >
                    {{ typeof item === 'string' ? item : stringify(item) }}
                  </div>
                </div>
              </template>
              <template v-else-if="value && typeof value === 'object' && Object.keys(value).length > 0">
                <el-descriptions :column="1" size="small" border>
                  <el-descriptions-item
                    v-for="(objValue, objKey) in value"
                    :key="objKey"
                    :label="objKey"
                  >
                    {{ typeof objValue === 'string' ? objValue : stringify(objValue) }}
                  </el-descriptions-item>
                </el-descriptions>
              </template>
              <template v-else>
                <el-empty description="暂无数据" :image-size="80" />
              </template>
            </template>
          </el-card>
        </template>

        <!-- 时间线与影响范围 -->
        <el-card v-if="getTimeline(diagnosisDrawer.record) || getImpactScope(diagnosisDrawer.record)" shadow="never" class="json-card">
          <template #header>
            <span>时间线与影响范围</span>
          </template>
          
          <!-- 时间线 -->
          <div v-if="getTimeline(diagnosisDrawer.record)" class="timeline-section">
            <h4>时间线</h4>
            <div class="timeline-container">
              <el-timeline>
                <el-timeline-item
                  timestamp="问题开始"
                  placement="top"
                  type="primary"
                  size="large"
                >
                  <div class="timeline-card">
                    <div class="timeline-time">
                      <el-icon><Clock /></el-icon>
                      <span>{{ formatDateTime(getTimeline(diagnosisDrawer.record).problem_start) }}</span>
                    </div>
                  </div>
                </el-timeline-item>
                
                <el-timeline-item
                  v-for="(event, idx) in getTimeline(diagnosisDrawer.record).key_events || []"
                  :key="idx"
                  timestamp="关键事件"
                  placement="top"
                  type="warning"
                  size="large"
                >
                  <div class="timeline-card timeline-event-card">
                    <div class="timeline-event">
                      <el-icon class="event-icon"><Bell /></el-icon>
                      <div class="event-text">{{ event }}</div>
                    </div>
                  </div>
                </el-timeline-item>
                
                <el-timeline-item
                  timestamp="问题恶化"
                  placement="top"
                  type="danger"
                  size="large"
                >
                  <div class="timeline-card">
                    <div class="timeline-time">
                      <el-icon><WarningFilled /></el-icon>
                      <span>{{ formatDateTime(getTimeline(diagnosisDrawer.record).problem_escalate) }}</span>
                    </div>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>
          
          <!-- 影响范围 -->
          <div v-if="getImpactScope(diagnosisDrawer.record)" class="impact-section">
            <h4>影响范围</h4>
            <div class="impact-container">
              <div class="impact-grid">
                <!-- 受影响的 Pod -->
                <div v-if="getImpactScope(diagnosisDrawer.record).affected_pods?.length" class="impact-item impact-item-pod">
                  <div class="impact-label">
                    <el-icon><Box /></el-icon>
                    <span>受影响的 Pod</span>
                    <el-tag size="small" type="info" class="impact-count">{{ getImpactScope(diagnosisDrawer.record).affected_pods.length }}</el-tag>
                  </div>
                  <div class="impact-tags">
                    <el-tag
                      v-for="pod in getImpactScope(diagnosisDrawer.record).affected_pods"
                      :key="pod"
                      type="primary"
                      effect="plain"
                      class="impact-tag"
                    >
                      {{ pod }}
                    </el-tag>
                  </div>
                </div>
                
                <!-- 受影响的服务 -->
                <div v-if="getImpactScope(diagnosisDrawer.record).affected_services?.length" class="impact-item impact-item-service">
                  <div class="impact-label">
                    <el-icon><Connection /></el-icon>
                    <span>受影响的服务</span>
                    <el-tag size="small" type="warning" class="impact-count">{{ getImpactScope(diagnosisDrawer.record).affected_services.length }}</el-tag>
                  </div>
                  <div class="impact-tags">
                    <el-tag
                      v-for="svc in getImpactScope(diagnosisDrawer.record).affected_services"
                      :key="svc"
                      type="warning"
                      effect="plain"
                      class="impact-tag"
                    >
                      {{ svc }}
                    </el-tag>
                  </div>
                </div>
                
                <!-- 受影响的节点 -->
                <div v-if="getImpactScope(diagnosisDrawer.record).affected_nodes?.length" class="impact-item impact-item-node">
                  <div class="impact-label">
                    <el-icon><Monitor /></el-icon>
                    <span>受影响的节点</span>
                    <el-tag size="small" type="danger" class="impact-count">{{ getImpactScope(diagnosisDrawer.record).affected_nodes.length }}</el-tag>
                  </div>
                  <div class="impact-tags">
                    <el-tag
                      v-for="node in getImpactScope(diagnosisDrawer.record).affected_nodes"
                      :key="node"
                      type="danger"
                      effect="plain"
                      class="impact-tag"
                    >
                      {{ node }}
                    </el-tag>
                  </div>
                </div>
              </div>
              
              <!-- 业务影响 -->
              <div 
                class="business-impact"
                :class="{
                  'business-impact-high': getImpactScope(diagnosisDrawer.record).business_impact === 'high',
                  'business-impact-medium': getImpactScope(diagnosisDrawer.record).business_impact === 'medium',
                  'business-impact-low': getImpactScope(diagnosisDrawer.record).business_impact === 'low'
                }"
              >
                <div class="business-impact-label">
                  <el-icon><TrendCharts /></el-icon>
                  <span>业务影响</span>
                </div>
                <el-tag
                  :type="getImpactScope(diagnosisDrawer.record).business_impact === 'high' ? 'danger' : getImpactScope(diagnosisDrawer.record).business_impact === 'medium' ? 'warning' : 'success'"
                  size="large"
                  effect="dark"
                  class="business-impact-tag"
                >
                  <el-icon v-if="getImpactScope(diagnosisDrawer.record).business_impact === 'high'"><WarningFilled /></el-icon>
                  <el-icon v-else-if="getImpactScope(diagnosisDrawer.record).business_impact === 'medium'"><InfoFilled /></el-icon>
                  <el-icon v-else><CircleCheckFilled /></el-icon>
                  {{ getImpactScope(diagnosisDrawer.record).business_impact === 'high' ? '高' : getImpactScope(diagnosisDrawer.record).business_impact === 'medium' ? '中' : '低' }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>

        <el-card v-if="getStructuredSolutions(diagnosisDrawer.record)" shadow="never" class="json-card">
          <template #header>
            <span>解决方案</span>
          </template>
          <div v-if="getStructuredSolutions(diagnosisDrawer.record)">
            <el-tabs>
              <el-tab-pane v-if="getStructuredSolutions(diagnosisDrawer.record).immediate?.length" label="立即缓解措施">
                <div v-for="(solution, idx) in getStructuredSolutions(diagnosisDrawer.record).immediate" :key="idx" class="solution-item">
                  <el-card shadow="hover" style="margin-bottom: 16px">
                    <template #header>
                      <div style="display: flex; justify-content: space-between; align-items: center">
                        <span>{{ solution.title }}</span>
                        <el-tag :type="solution.priority === 'high' ? 'danger' : solution.priority === 'medium' ? 'warning' : 'info'" size="small">
                          {{ solution.priority === 'high' ? '高优先级' : solution.priority === 'medium' ? '中优先级' : '低优先级' }}
                        </el-tag>
                      </div>
                    </template>
                    <div v-if="solution.steps?.length" class="solution-steps">
                      <h5>操作步骤：</h5>
                      <ol>
                        <li v-for="(step, stepIdx) in solution.steps" :key="stepIdx" style="margin-bottom: 8px">
                          <div><strong>{{ step.action }}</strong></div>
                          <div v-if="step.command" class="command-box">
                            <code>{{ step.command }}</code>
                          </div>
                          <div v-if="step.description" class="step-description">
                            {{ step.description }}
                          </div>
                        </li>
                      </ol>
                    </div>
                    <div v-if="solution.risk" class="solution-risk">
                      <el-tag :type="solution.risk === 'high' ? 'danger' : solution.risk === 'medium' ? 'warning' : 'success'" size="small">
                        风险等级：{{ solution.risk === 'high' ? '高' : solution.risk === 'medium' ? '中' : '低' }}
                      </el-tag>
                    </div>
                    <div v-if="solution.rollback" class="solution-rollback">
                      <h5>回滚方案：</h5>
                      <div v-if="solution.rollback.command" class="command-box">
                        <code>{{ solution.rollback.command }}</code>
                      </div>
                      <div v-if="solution.rollback.description" class="step-description">
                        {{ solution.rollback.description }}
                      </div>
                    </div>
                  </el-card>
                </div>
              </el-tab-pane>
              <el-tab-pane v-if="getStructuredSolutions(diagnosisDrawer.record).root?.length" label="根本解决方案">
                <div v-for="(solution, idx) in getStructuredSolutions(diagnosisDrawer.record).root" :key="idx" class="solution-item">
                  <el-card shadow="hover" style="margin-bottom: 16px">
                    <template #header>
                      <div style="display: flex; justify-content: space-between; align-items: center">
                        <span>{{ solution.title }}</span>
                        <el-tag :type="solution.priority === 'high' ? 'danger' : solution.priority === 'medium' ? 'warning' : 'info'" size="small">
                          {{ solution.priority === 'high' ? '高优先级' : solution.priority === 'medium' ? '中优先级' : '低优先级' }}
                        </el-tag>
                      </div>
                    </template>
                    <div v-if="solution.steps?.length" class="solution-steps">
                      <h5>操作步骤：</h5>
                      <ol>
                        <li v-for="(step, stepIdx) in solution.steps" :key="stepIdx" style="margin-bottom: 8px">
                          <div><strong>{{ step.action }}</strong></div>
                          <div v-if="step.command" class="command-box">
                            <code>{{ step.command }}</code>
                          </div>
                          <div v-if="step.description" class="step-description">
                            {{ step.description }}
                          </div>
                        </li>
                      </ol>
                    </div>
                    <div v-if="solution.risk" class="solution-risk">
                      <el-tag :type="solution.risk === 'high' ? 'danger' : solution.risk === 'medium' ? 'warning' : 'success'" size="small">
                        风险等级：{{ solution.risk === 'high' ? '高' : solution.risk === 'medium' ? '中' : '低' }}
                      </el-tag>
                    </div>
                    <div v-if="solution.verification" class="solution-verification">
                      <h5>验证方法：</h5>
                      <div v-if="solution.verification.expected" class="step-description">
                        预期结果：{{ solution.verification.expected }}
                      </div>
                    </div>
                  </el-card>
                </div>
              </el-tab-pane>
              <el-tab-pane v-if="getStructuredSolutions(diagnosisDrawer.record).preventive?.length" label="预防措施">
                <ul>
                  <li v-for="(measure, idx) in getStructuredSolutions(diagnosisDrawer.record).preventive" :key="idx" style="margin-bottom: 8px">
                    {{ measure }}
                  </li>
                </ul>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>

        <!-- 诊断报告（当状态为 pending_human 时） -->
        <el-card v-if="diagnosisDrawer.record && diagnosisDrawer.record.status === 'pending_human' && diagnosisReport" shadow="never" class="json-card">
          <template #header>
            <span>诊断报告</span>
          </template>
          <div v-if="diagnosisReport?.has_report && diagnosisReport?.report">
            <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
              经过 {{ diagnosisReport.report.summary?.diagnosis_duration || '多轮' }} 迭代，系统无法确定根因，建议人工介入排查。
            </el-alert>
            <el-descriptions border :column="1" size="small">
              <el-descriptions-item label="问题描述">
                {{ diagnosisReport.report.summary?.problem }}
              </el-descriptions-item>
              <el-descriptions-item label="最终置信度">
                <el-progress :percentage="Math.round((diagnosisReport.report.summary?.final_confidence || 0) * 100)" status="exception" />
              </el-descriptions-item>
            </el-descriptions>
            <div v-if="diagnosisReport.report.collected_information" style="margin-top: 16px">
              <h4>已收集的信息</h4>
              <el-tag v-if="diagnosisReport.report.collected_information.metrics" type="success" style="margin-right: 8px">指标数据</el-tag>
              <el-tag v-if="diagnosisReport.report.collected_information.logs" type="success" style="margin-right: 8px">日志数据</el-tag>
              <el-tag v-if="diagnosisReport.report.collected_information.k8s_resources" type="success" style="margin-right: 8px">K8s 资源</el-tag>
              <el-tag v-if="diagnosisReport.report.collected_information.deep_context" type="success" style="margin-right: 8px">深度上下文</el-tag>
              <el-tag v-if="diagnosisReport.report.collected_information.events" type="success" style="margin-right: 8px">事件</el-tag>
              <el-tag v-if="diagnosisReport.report.collected_information.knowledge_base" type="success" style="margin-right: 8px">知识库</el-tag>
            </div>
            <div v-if="diagnosisReport.report.recommended_actions" style="margin-top: 16px">
              <h4>建议的排查方向</h4>
              <el-collapse>
                <el-collapse-item title="立即检查" name="immediate">
                  <ul>
                    <li v-for="(action, idx) in diagnosisReport.report.recommended_actions.immediate_checks" :key="idx" style="margin-bottom: 4px">
                      {{ action }}
                    </li>
                  </ul>
                </el-collapse-item>
                <el-collapse-item title="进一步调查" name="further">
                  <ul>
                    <li v-for="(action, idx) in diagnosisReport.report.recommended_actions.further_investigation" :key="idx" style="margin-bottom: 4px">
                      {{ action }}
                    </li>
                  </ul>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </el-card>

          </div>
        </div>

        <div class="diagnosis-raw">
        <el-collapse>
          <el-collapse-item title="指标数据" name="metrics">
            <pre class="json-preview">{{ stringify(diagnosisDrawer.record.metrics) }}</pre>
          </el-collapse-item>
          <el-collapse-item title="日志摘要" name="logs">
            <pre class="json-preview">{{ stringify(diagnosisDrawer.record.logs) }}</pre>
          </el-collapse-item>
          <el-collapse-item title="原始建议数据" name="recommendations">
            <pre class="json-preview">{{ stringify(diagnosisDrawer.record.recommendations) }}</pre>
          </el-collapse-item>
        </el-collapse>

        <el-divider />

        <el-form :model="feedbackForm" label-width="110px" class="feedback-form">
          <el-alert
            v-if="feedbackState || feedbackLatest"
            :title="feedbackState ? `上次反馈：${formatFeedbackType(feedbackState.last_feedback_type)}` : '历史反馈'"
            type="info"
            :closable="false"
            show-icon
            class="feedback-alert"
          >
            <p v-if="feedbackStateDescription">{{ feedbackStateDescription }}</p>
            <p v-if="feedbackLatest?.submitted_at">最近提交时间：{{ formatDateTime(feedbackLatest.submitted_at) }}</p>
            <p v-if="feedbackLatest?.feedback_notes">最近备注：{{ feedbackLatest.feedback_notes }}</p>
            <p v-if="feedbackLatest?.action_taken">已采取动作：{{ feedbackLatest.action_taken }}</p>
          </el-alert>

          <el-form-item label="反馈类型" required>
            <el-select v-model="feedbackForm.feedback_type" placeholder="请选择反馈类型">
              <el-option
                v-for="option in feedbackOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              >
                <div class="feedback-option">
                  <span class="option-label">{{ option.label }}</span>
                  <span class="option-desc">{{ option.description }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item v-if="iterationOptions.length" label="关联迭代">
            <el-select v-model="feedbackForm.iteration_no" placeholder="选择对应的诊断迭代">
              <el-option
                v-for="iteration in iterationOptions"
                :key="iteration.value"
                :label="iteration.label"
                :value="iteration.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="反馈说明" :required="requiresFeedbackNotes">
            <el-input
              v-model="feedbackForm.feedback_notes"
              type="textarea"
              :rows="3"
              :placeholder="feedbackNotesPlaceholder"
            />
          </el-form-item>

          <el-form-item label="已采取的行动">
            <el-input
              v-model="feedbackForm.action_taken"
              type="textarea"
              :rows="2"
              placeholder="可选，如：已重启 Pod / 回滚配置"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitFeedback">提交反馈</el-button>
          </el-form-item>
        </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="diagnosisDrawer.visible = false">关 闭</el-button>
      </template>
    </el-drawer>

    <!-- 手动诊断 -->
    <el-dialog
      v-model="diagnosisDialog.visible"
      title="发起手动诊断"
      width="560px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div class="manual-diagnosis">
        <el-alert
          class="manual-diagnosis__alert"
          type="info"
          show-icon
          :closable="false"
          title="选择目标集群与资源，系统将基于指标与日志进行深入诊断。"
        />
        <el-form :model="diagnosisDialog.form" label-width="110px" class="manual-diagnosis__form">
          <el-form-item label="集群">
            <el-select 
              v-model="diagnosisDialog.form.cluster_id" 
              placeholder="选择集群" 
              style="width: 100%"
              popper-class="diagnosis-select-popper"
              teleported
              @change="handleDiagnosisClusterChange"
            >
              <el-option
                v-for="cluster in clusters"
                :key="cluster.id"
                :label="cluster.name"
                :value="cluster.id"
              />
            </el-select>
            <p v-if="!clusters.length" class="manual-diagnosis__hint">暂无可用集群，请先完成集群接入</p>
          </el-form-item>

          <el-form-item label="命名空间">
            <el-select
              v-model="diagnosisDialog.form.namespace"
              placeholder="选择命名空间"
              :loading="diagnosisNamespaceLoading"
              :disabled="!diagnosisDialog.form.cluster_id"
              style="width: 100%"
              filterable
              clearable
              popper-class="diagnosis-select-popper"
              teleported
              @change="handleDiagnosisNamespaceChange"
            >
              <el-option
                v-for="ns in diagnosisNamespaces"
                :key="ns"
                :label="ns"
                :value="ns"
              />
              <el-option 
                v-if="!diagnosisNamespaceLoading && diagnosisDialog.form.cluster_id && diagnosisNamespaces.length === 0"
                disabled 
                label="暂无命名空间数据" 
                value="" 
              />
              <el-option 
                v-if="!diagnosisDialog.form.cluster_id"
                disabled 
                label="请先选择集群" 
                value="" 
              />
            </el-select>
          </el-form-item>

          <el-form-item label="资源类型">
            <el-select 
              v-model="diagnosisDialog.form.resource_type" 
              style="width: 100%"
              popper-class="diagnosis-select-popper"
              teleported
              @change="handleDiagnosisResourceTypeChange"
            >
              <el-option label="Pod" value="pods" />
              <el-option label="Node" value="nodes" />
              <el-option label="Deployment" value="deployments" />
              <el-option label="StatefulSet" value="statefulsets" />
              <el-option label="DaemonSet" value="daemonsets" />
              <el-option label="Service" value="services" />
            </el-select>
          </el-form-item>

          <el-form-item label="资源名称">
            <el-select
              v-model="diagnosisDialog.form.resource_name"
              placeholder="选择资源"
              :loading="diagnosisResourceLoading"
              :disabled="!diagnosisDialog.form.cluster_id || !diagnosisDialog.form.resource_type || (diagnosisDialog.form.resource_type !== 'nodes' && !diagnosisDialog.form.namespace)"
              style="width: 100%"
              filterable
              popper-class="diagnosis-select-popper"
              teleported
            >
              <el-option
                v-for="resource in diagnosisResources"
                :key="resource"
                :label="resource"
                :value="resource"
              />
              <el-option 
                v-if="!diagnosisResourceLoading && diagnosisResources.length === 0"
                disabled 
                label="暂无资源数据" 
                value="" 
              />
              <el-option 
                v-if="diagnosisDialog.form.resource_type !== 'nodes' && !diagnosisDialog.form.namespace"
                disabled 
                label="请先选择命名空间" 
                value="" 
              />
            </el-select>
            <p class="manual-diagnosis__hint" style="color: #909399; font-size: 12px;">
              资源列表: {{ diagnosisResources.length }} 个
            </p>
          </el-form-item>

          <el-form-item label="时间范围">
            <el-select
              v-model="diagnosisDialog.form.time_range_hours"
              placeholder="选择监控数据时间范围"
              style="width: 100%"
              popper-class="diagnosis-select-popper"
              teleported
            >
              <el-option label="1小时" :value="1.0" />
              <el-option label="2小时" :value="2.0" />
              <el-option label="4小时" :value="4.0" />
              <el-option label="12小时" :value="12.0" />
              <el-option label="24小时" :value="24.0" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="diagnosisDialog.visible = false">取 消</el-button>
        <el-button
          type="primary"
          :loading="diagnosisDialog.submitting"
          :disabled="!diagnosisDialog.form.cluster_id || !diagnosisDialog.form.resource_name"
          @click="submitManualDiagnosis"
        >
          开始诊断
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" src="./index.ts"></script>

<style lang="scss" scoped src="./index.scss"></style>
