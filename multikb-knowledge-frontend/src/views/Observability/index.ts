import { computed, reactive, ref, watch, onMounted, onUnmounted, onUpdated, nextTick, defineComponent } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import {
  fetchClusters,
  createCluster,
  updateCluster,
  deleteCluster,
  testClusterConnectivity,
  runClusterHealthCheck,
  syncClusterResources,
  fetchResourceSnapshots,
  fetchClusterNamespaces,
  fetchClusterPods,
  queryMetrics,
  queryLogs,
  listDiagnosisRecords,
  getDiagnosisRecord,
  runDiagnosis,
  submitDiagnosisFeedback,
  listDiagnosisIterations,
  listDiagnosisMemories,
  getDiagnosisReport,
  deleteDiagnosisRecord
} from '@/api/modules/observability'
import type {
  ClusterConfig,
  ClusterConnectivityResult,
  ResourceSnapshot,
  ResourceSyncResult,
  MetricsQueryResult,
  LogQueryResult,
  DiagnosisRecord,
  DiagnosisIteration,
  DiagnosisMemory,
  SubmitDiagnosisFeedbackPayload,
  DiagnosisFeedbackState,
  DiagnosisFeedbackEntry
} from '@/types'
import { formatDateTime } from '@/utils/format'
import { 
  Monitor, 
  ArrowDown, 
  MoreFilled, 
  Edit, 
  Delete,
  WarningFilled,
  InfoFilled,
  CircleCheckFilled,
  CircleCloseFilled,
  Document,
  Setting,
  Bell,
  DataAnalysis,
  Clock,
  Box,
  Connection,
  TrendCharts
} from '@element-plus/icons-vue'

export default defineComponent({
  name: 'ObservabilityPage',
  components: {
    Monitor,
    ArrowDown,
    MoreFilled,
    Edit,
    Delete,
    WarningFilled,
    InfoFilled,
    CircleCheckFilled,
    CircleCloseFilled,
    Document,
    Setting,
    Bell,
    DataAnalysis,
    Clock,
    Box,
    Connection,
    TrendCharts
  },
  setup() {
    const activeTab = ref('clusters')
    const pageLoading = ref(false)

    const isAuthError = (error: unknown): boolean => {
      const err = error as any
      return !!(err?.isAuthError || err?.code === 401 || err?.response?.status === 401)
    }

    const PROM_AUTH_OPTIONS = [
      { label: '无认证', value: 'none' },
      { label: 'Basic', value: 'basic' },
      { label: 'Bearer Token', value: 'token' }
    ]

    const LOG_AUTH_OPTIONS = [
      { label: '无认证', value: 'none' },
      { label: 'Basic', value: 'basic' },
      { label: 'Bearer Token', value: 'token' }
    ]

    const FEEDBACK_OPTIONS = [
      {
        value: 'confirmed',
        label: '已确认根因',
        description: '确认诊断结论正确，并沉淀为知识库案例'
      },
      {
        value: 'continue_investigation',
        label: '继续排查',
        description: '当前结论不可信，需要继续执行后续步骤收集更多信息'
      },
      {
        value: 'custom',
        label: '其他反馈',
        description: '自定义反馈内容（需要填写具体说明）'
      }
    ] as const

    const createEmptyClusterForm = (): Record<string, any> => ({
      name: '',
      api_server: '',
      auth_type: 'token',
      auth_token: '',
      kubeconfig: '',
      client_cert: '',
      client_key: '',
      ca_cert: '',
      verify_ssl: true,
      prometheus_url: '',
      prometheus_auth_type: 'none',
      prometheus_username: '',
      prometheus_password: '',
      log_system: '',
      log_endpoint: '',
      log_auth_type: 'none',
      log_username: '',
      log_password: '',
      is_active: true
    })

    // 集群管理
    const clusters = ref<ClusterConfig[]>([])
    const clusterPagination = reactive({
      page: 1,
      size: 10,
      total: 0
    })
    const clusterDialog = reactive({
      visible: false,
      editing: false,
      form: createEmptyClusterForm()
    })
    const clusterFormRef = ref()

    const clusterRules = {
      name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
      api_server: [{ required: true, message: '请输入 API Server', trigger: 'blur' }]
    }

    watch(
      () => clusterDialog.form.prometheus_auth_type,
      (type) => {
        if (type !== 'basic') {
          clusterDialog.form.prometheus_username = ''
        }
        if (type === 'none') {
          clusterDialog.form.prometheus_password = ''
        }
      }
    )

    watch(
      () => clusterDialog.form.prometheus_url,
      (url) => {
        if (!url) {
          clusterDialog.form.prometheus_auth_type = 'none'
          clusterDialog.form.prometheus_username = ''
          clusterDialog.form.prometheus_password = ''
        }
      }
    )

    watch(
      () => clusterDialog.form.log_auth_type,
      (type) => {
        if (type !== 'basic') {
          clusterDialog.form.log_username = ''
        }
        if (type === 'none') {
          clusterDialog.form.log_password = ''
        }
      }
    )

    watch(
      () => clusterDialog.form.log_system,
      (system) => {
        if (!system) {
          clusterDialog.form.log_auth_type = 'none'
          clusterDialog.form.log_username = ''
          clusterDialog.form.log_password = ''
        }
      }
    )

    const loadClusters = async () => {
      pageLoading.value = true
      try {
        const res = await fetchClusters({
          page: clusterPagination.page,
          size: clusterPagination.size
        })
        const data = (res as any)?.data || {}
        const clusterList = Array.isArray(data.list) ? data.list : []
        clusters.value = clusterList.filter((item: any) => item && item.id && item.name)
        clusterPagination.total = data.total ?? 0
        if (clusters.value.length && !resourceFilters.clusterId) {
          resourceFilters.clusterId = clusters.value[0].id
          metricsForm.cluster_id = clusters.value[0].id
          logForm.cluster_id = clusters.value[0].id
          // 只有在对话框没有打开时才设置默认集群ID
          if (!diagnosisDialog.visible) {
          diagnosisDialog.form.cluster_id = clusters.value[0].id
          }
        }
      } catch (error: any) {
        console.error('[ERROR] 加载集群失败:', error)
        clusters.value = []
        clusterPagination.total = 0
        if (isAuthError(error)) {
          ElMessage.warning('请先登录')
        } else {
          const errorMsg = error?.response?.data?.detail || error?.message || '加载集群失败'
          ElMessage.error(typeof errorMsg === 'string' ? errorMsg : '加载集群失败，请检查网络连接')
        }
      } finally {
        pageLoading.value = false
      }
    }

    const openClusterDialog = (record?: ClusterConfig) => {
      clusterDialog.editing = !!record
      clusterDialog.visible = true
      clusterDialog.form = record
        ? {
            ...createEmptyClusterForm(),
            ...record,
            auth_token: '',
            kubeconfig: '',
            client_cert: '',
            client_key: '',
            ca_cert: '',
            prometheus_password: '',
            log_password: ''
          }
        : createEmptyClusterForm()
      nextTick(() => {
        clusterFormRef.value?.clearValidate()
      })
    }

    const buildClusterPayload = (isEditing: boolean) => {
      const payload = { ...clusterDialog.form }
      if (payload.auth_type === 'kubeconfig') {
        payload.auth_token = undefined
        if (!payload.kubeconfig) {
          payload.kubeconfig = undefined
          if (!isEditing) {
            throw new Error('KUBECONFIG_REQUIRED')
          }
        }
      } else {
        payload.kubeconfig = undefined
        if (!payload.auth_token) {
          payload.auth_token = undefined
        }
      }

      // 处理 Prometheus URL：空字符串转为 undefined
      if (!payload.prometheus_url || payload.prometheus_url.trim() === '') {
        payload.prometheus_url = undefined
        payload.prometheus_auth_type = 'none'
        payload.prometheus_username = undefined
        payload.prometheus_password = undefined
      } else if (payload.prometheus_auth_type === 'basic') {
        if (!payload.prometheus_username) {
          throw new Error('PROM_BASIC_REQUIRED')
        }
        if (!payload.prometheus_password) {
          if (!isEditing) {
            throw new Error('PROM_BASIC_REQUIRED')
          }
          payload.prometheus_password = undefined
        }
      } else if (payload.prometheus_auth_type === 'token') {
        if (!payload.prometheus_password) {
          if (!isEditing) {
            throw new Error('PROM_TOKEN_REQUIRED')
          }
          payload.prometheus_password = undefined
        }
        payload.prometheus_username = undefined
      } else {
        payload.prometheus_username = undefined
        payload.prometheus_password = undefined
      }

      // 处理日志系统：如果未选择日志系统，清空相关字段
      if (!payload.log_system || payload.log_system.trim() === '') {
        payload.log_system = undefined
        payload.log_endpoint = undefined
        payload.log_auth_type = 'none'
        payload.log_username = undefined
        payload.log_password = undefined
      } else if (!payload.log_endpoint || payload.log_endpoint.trim() === '') {
        // 如果选择了日志系统但未填写入口地址，也清空
        payload.log_endpoint = undefined
        payload.log_auth_type = 'none'
        payload.log_username = undefined
        payload.log_password = undefined
      } else if (payload.log_auth_type === 'basic') {
        if (!payload.log_username) {
          throw new Error('LOG_BASIC_REQUIRED')
        }
        if (!payload.log_password) {
          if (!isEditing) {
            throw new Error('LOG_BASIC_REQUIRED')
          }
          payload.log_password = undefined
        }
      } else if (payload.log_auth_type === 'token') {
        if (!payload.log_password) {
          if (!isEditing) {
            throw new Error('LOG_TOKEN_REQUIRED')
          }
          payload.log_password = undefined
        }
        payload.log_username = undefined
      } else {
        payload.log_username = undefined
        payload.log_password = undefined
      }

      // 处理证书字段：如果为空则设为 undefined（编辑时留空表示不更新）
      if (!payload.client_cert) {
        payload.client_cert = undefined
      }
      if (!payload.client_key) {
        payload.client_key = undefined
      }
      if (!payload.ca_cert) {
        payload.ca_cert = undefined
      }

      return payload
    }

    const submitClusterForm = async () => {
      await clusterFormRef.value?.validate()
      try {
        const payload = buildClusterPayload(clusterDialog.editing)
        if (clusterDialog.editing) {
          await updateCluster(clusterDialog.form.id, payload)
          ElMessage.success('更新成功')
        } else {
          await createCluster(payload)
          ElMessage.success('创建成功')
        }
        clusterDialog.visible = false
        loadClusters()
      } catch (error: any) {
        const code = error?.message
        if (code === 'PROM_BASIC_REQUIRED') {
          ElMessage.warning('Prometheus Basic 认证需要填写用户名和密码')
        } else if (code === 'PROM_TOKEN_REQUIRED') {
          ElMessage.warning('请填写 Prometheus Token')
        } else if (code === 'LOG_BASIC_REQUIRED') {
          ElMessage.warning('日志系统 Basic 认证需要填写用户名和密码')
        } else if (code === 'LOG_TOKEN_REQUIRED') {
          ElMessage.warning('请填写日志系统 Token')
        } else if (code === 'KUBECONFIG_REQUIRED') {
          ElMessage.warning('请上传 kubeconfig 凭证')
        } else if (!isAuthError(error)) {
          // 显示详细的验证错误信息
          const errorMsg = error?.response?.data?.detail || error?.message || '保存失败'
          if (typeof errorMsg === 'string') {
            ElMessage.error(`保存失败: ${errorMsg}`)
          } else if (Array.isArray(errorMsg)) {
            // Pydantic 验证错误通常是数组格式
            const firstError = errorMsg[0]
            if (firstError?.loc && firstError?.msg) {
              const field = firstError.loc.join('.')
              ElMessage.error(`保存失败: ${field} - ${firstError.msg}`)
            } else {
              ElMessage.error(`保存失败: ${JSON.stringify(errorMsg)}`)
            }
          } else {
            ElMessage.error('保存失败')
          }
        }
      }
    }

    const handleDeleteCluster = async (record: ClusterConfig) => {
      try {
        await ElMessageBox.confirm(`确认删除集群【${record.name}】吗？`, '提示', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        })
        await deleteCluster(record.id)
        ElMessage.success('删除成功')
        loadClusters()
      } catch (error) {
        // ignore cancel
        if (!isAuthError(error)) {
          ElMessage.error('删除失败')
        }
      }
    }

    const connectivityDialog = reactive<{
      visible: boolean
      result: ClusterConnectivityResult | null
    }>({
      visible: false,
      result: null
    })

    const handleTestConnectivity = async (record: ClusterConfig) => {
      try {
        const res = await testClusterConnectivity(record.id)
        connectivityDialog.result = (res as any).data
        connectivityDialog.visible = true
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('连通性测试失败')
        }
      }
    }

    const handleHealthCheck = async (record: ClusterConfig) => {
      try {
        await runClusterHealthCheck(record.id)
        ElNotification.success({
          title: '健康检查',
          message: '健康检查任务已触发'
        })
        loadClusters()
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('健康检查触发失败')
        }
      }
    }

    // 资源快照
    const resourceTypeOptions = [
      { label: 'Pods', value: 'pods' },
      { label: 'Deployments', value: 'deployments' },
      { label: 'StatefulSets', value: 'statefulsets' },
      { label: 'DaemonSets', value: 'daemonsets' },
      { label: 'Jobs', value: 'jobs' },
      { label: 'CronJobs', value: 'cronjobs' },
      { label: 'Services', value: 'services' },
      { label: 'ConfigMaps', value: 'configmaps' },
      { label: 'Events', value: 'events' },
      { label: 'Nodes', value: 'nodes' }
    ]

    const resourceFilters = reactive({
      clusterId: 0,
      resourceType: 'pods',
      namespace: '',
      page: 1,
      size: 10
    })
    const resourcePagination = reactive({
      total: 0
    })
    const resourceSnapshots = ref<ResourceSnapshot[]>([])
    const resourceLoading = ref(false)
    const recentSyncEvents = ref<
      Array<{ timestamp: string; type: string; message: string; diff?: Record<string, any>; uid: string }>
    >([])

    const loadResources = async (resetPage = false) => {
      if (!resourceFilters.clusterId) return
      if (resetPage) {
        resourceFilters.page = 1
      }
      resourceLoading.value = true
      try {
        const res = await fetchResourceSnapshots(resourceFilters.clusterId, {
          page: resourceFilters.page,
          size: resourceFilters.size,
          resource_type: resourceFilters.resourceType || undefined,
          namespace: resourceFilters.namespace || undefined
        })
        const data = (res as any).data || {}
        resourceSnapshots.value = data.list ?? []
        resourcePagination.total = data.total ?? 0
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('加载资源快照失败')
        } else {
          resourceSnapshots.value = []
          resourcePagination.total = 0
        }
      } finally {
        resourceLoading.value = false
      }
    }

    const handleResourcePageChange = (page: number) => {
      resourceFilters.page = page
      loadResources()
    }

    const handleManualSync = async () => {
      if (!resourceFilters.clusterId) {
        ElMessage.warning('请先选择集群')
        return
      }
      try {
        const res = await syncClusterResources(resourceFilters.clusterId, {
          namespace: resourceFilters.namespace || undefined,
          resource_types: [resourceFilters.resourceType],
          limit: resourceFilters.size
        })
        const data = (res as any).data || {}
        const syncResult = data[resourceFilters.resourceType] as ResourceSyncResult
        if (syncResult?.events) {
          recentSyncEvents.value = syncResult.events.map((item) => ({
            timestamp: formatDateTime(new Date().toISOString()),
            type: item.type,
            message: `资源 ${item.uid} ${item.type}`,
            diff: item.diff,
            uid: item.uid
          }))
        }
        ElMessage.success(`同步完成，变更 ${syncResult?.events?.length || 0} 条`)
        loadResources()
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('同步失败')
        }
      }
    }

    // 指标分析
    const metricTemplateOptions = [
      { label: 'Pod CPU 使用率', value: 'pod_cpu_usage' },
      { label: 'Pod 内存使用', value: 'pod_memory_usage' },
      { label: 'Pod 重启速率', value: 'pod_restart_rate' },
      { label: 'Node CPU 总量', value: 'node_cpu_total' },
      { label: 'Node 内存使用', value: 'node_memory_usage' }
    ]

    const defaultTimeRange: [Date, Date] = [
      new Date(Date.now() - 30 * 60 * 1000),
      new Date()
    ]

    const metricsForm = reactive({
      cluster_id: 0,
      template_id: 'pod_cpu_usage',
      promql: '',
      range: defaultTimeRange as [Date, Date],
      step_seconds: 60,
      context: {
        namespace: '',
        pod: '',
        window: '5m'
      }
    })
    const metricsResult = ref<MetricsQueryResult | null>(null)

    // 命名空间和 Pod 列表
    const namespaces = ref<string[]>([])
    const pods = ref<string[]>([])
    const namespaceLoading = ref(false)
    const podLoading = ref(false)

    // 加载命名空间列表
    const loadNamespaces = async (clusterId: number) => {
      if (!clusterId) {
        namespaces.value = []
        metricsForm.context.namespace = ''
        return
      }
      namespaceLoading.value = true
      try {
        const res = await fetchClusterNamespaces(clusterId)
        namespaces.value = (res as any).data || []
        // 如果当前命名空间不在列表中，清空
        if (metricsForm.context.namespace && !namespaces.value.includes(metricsForm.context.namespace)) {
          metricsForm.context.namespace = ''
          metricsForm.context.pod = ''
          pods.value = []
        }
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('加载命名空间列表失败')
        }
        namespaces.value = []
      } finally {
        namespaceLoading.value = false
      }
    }

    // 加载 Pod 列表
    const loadPods = async (clusterId: number, namespace: string) => {
      if (!clusterId || !namespace) {
        pods.value = []
        metricsForm.context.pod = ''
        return
      }
      podLoading.value = true
      try {
        const res = await fetchClusterPods(clusterId, namespace)
        pods.value = (res as any).data || []
        // 如果当前 Pod 不在列表中，清空
        if (metricsForm.context.pod && !pods.value.includes(metricsForm.context.pod)) {
          metricsForm.context.pod = ''
        }
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('加载Pod列表失败')
        }
        pods.value = []
      } finally {
        podLoading.value = false
      }
    }

    // 监听集群变化，加载命名空间列表
    watch(
      () => metricsForm.cluster_id,
      (clusterId) => {
        loadNamespaces(clusterId)
        metricsForm.context.namespace = ''
        metricsForm.context.pod = ''
        pods.value = []
      }
    )

    // 命名空间变化时，加载 Pod 列表
    const handleNamespaceChange = (namespace: string) => {
      metricsForm.context.pod = ''
      loadPods(metricsForm.cluster_id, namespace)
    }

    // 根据模板判断需要哪些参数
    const needsNamespace = computed(() => {
      const podTemplates = ['pod_cpu_usage', 'pod_memory_usage', 'pod_restart_rate']
      return metricsForm.template_id && podTemplates.includes(metricsForm.template_id)
    })

    const needsPod = computed(() => {
      const podTemplates = ['pod_cpu_usage', 'pod_memory_usage', 'pod_restart_rate']
      return metricsForm.template_id && podTemplates.includes(metricsForm.template_id)
    })

    const needsWindow = computed(() => {
      const windowTemplates = ['pod_cpu_usage', 'pod_restart_rate', 'node_cpu_total']
      return metricsForm.template_id && windowTemplates.includes(metricsForm.template_id)
    })

    const handleTemplateChange = () => {
      // 切换模板时，重置 context 中的默认值
      if (!needsNamespace.value) {
        metricsForm.context.namespace = ''
        metricsForm.context.pod = ''
        pods.value = []
      } else if (metricsForm.cluster_id && !metricsForm.context.namespace) {
        // 如果需要命名空间但没有选择，重新加载命名空间列表
        loadNamespaces(metricsForm.cluster_id)
      }
      if (!needsPod.value) {
        metricsForm.context.pod = ''
      }
      if (!needsWindow.value) {
        metricsForm.context.window = ''
      } else if (!metricsForm.context.window) {
        metricsForm.context.window = '5m'
      }
    }

    const handleQueryMetrics = async () => {
      if (!metricsForm.cluster_id) {
        ElMessage.warning('请选择集群')
        return
      }
      if (!metricsForm.template_id && !metricsForm.promql) {
        ElMessage.warning('请选择模板或填写 PromQL')
        return
      }

      // 验证模板所需的参数
      if (metricsForm.template_id && !metricsForm.promql) {
        if (needsNamespace.value && !metricsForm.context.namespace) {
          ElMessage.warning('请填写命名空间')
          return
        }
        if (needsPod.value && !metricsForm.context.pod) {
          ElMessage.warning('请填写Pod名称')
          return
        }
        if (needsWindow.value && !metricsForm.context.window) {
          ElMessage.warning('请填写时间窗口（如: 5m）')
          return
        }
      }

      try {
        const payload: Record<string, any> = {
          cluster_id: metricsForm.cluster_id,
          template_id: metricsForm.template_id || undefined,
          promql: metricsForm.promql || undefined,
          step_seconds: metricsForm.step_seconds || undefined
        }
        if (metricsForm.range && metricsForm.range.length === 2) {
          payload.start = metricsForm.range[0].toISOString()
          payload.end = metricsForm.range[1].toISOString()
        }
        // 如果使用模板，需要传递 context 参数
        if (metricsForm.template_id && !metricsForm.promql) {
          const context: Record<string, string> = {}
          if (needsNamespace.value && metricsForm.context.namespace) {
            context.namespace = metricsForm.context.namespace
          }
          if (needsPod.value && metricsForm.context.pod) {
            context.pod = metricsForm.context.pod
          }
          if (needsWindow.value && metricsForm.context.window) {
            context.window = metricsForm.context.window
          }
          if (Object.keys(context).length > 0) {
            payload.context = context
          }
        }
        const res = await queryMetrics(payload as any)
        metricsResult.value = (res as any).data
        ElMessage.success('指标查询成功')
      } catch (error) {
        metricsResult.value = null
        if (!isAuthError(error)) {
          ElMessage.error('指标查询失败')
        }
      }
    }

    const resetMetricsForm = () => {
      metricsForm.template_id = 'pod_cpu_usage'
      metricsForm.promql = ''
      metricsForm.range = [...defaultTimeRange]
      metricsForm.step_seconds = 60
      metricsForm.context = {
        namespace: '',
        pod: '',
        window: '5m'
      }
      metricsResult.value = null
      // 如果选择了集群，重新加载命名空间列表
      if (metricsForm.cluster_id) {
        loadNamespaces(metricsForm.cluster_id)
      }
    }

    const metricsSeries = computed(() => {
      if (!metricsResult.value?.data) return []
      const result = metricsResult.value.data?.result || []
      return result.map((item: any) => {
        const labels = item.metric || {}
        const values = item.values || (item.value ? [item.value] : [])
        const numeric = values
          .map((v: any[]) => parseFloat(v[1]))
          .filter((num: number) => !Number.isNaN(num))
        const latest = numeric.length ? numeric[numeric.length - 1] : null
        const average =
          numeric.length > 0
            ? Number((numeric.reduce((sum: number, num: number) => sum + num, 0) / numeric.length).toFixed(4))
            : null
        return {
          series: Object.entries(labels)
            .map(([key, value]) => `${key}=${value}`)
            .join(', '),
          labels,
          latest,
          average
        }
      })
    })

    // 图表配置
    const chartOptions = computed(() => {
      if (!metricsResult.value?.data) return null

      const result = metricsResult.value.data?.result || []
      if (result.length === 0) return null

      // 处理时间序列数据
      const series: any[] = []
      const xAxisData: string[] = []
      const allTimes = new Set<number>()

      // 收集所有时间点
      result.forEach((item: any) => {
        const values = item.values || (item.value ? [item.value] : [])
        values.forEach((v: any[]) => {
          allTimes.add(v[0])
        })
      })

      // 排序时间点
      const sortedTimes = Array.from(allTimes).sort((a, b) => a - b)

      // 构建 x 轴数据
      xAxisData.push(...sortedTimes.map((t) => {
        const date = new Date(t * 1000)
        return date.toLocaleString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      }))

      // 为每个时间序列创建系列
      result.forEach((item: any, index: number) => {
        const labels = item.metric || {}
        const values = item.values || (item.value ? [item.value] : [])

        // 创建时间到值的映射
        const valueMap = new Map<number, number>()
        values.forEach((v: any[]) => {
          valueMap.set(v[0], parseFloat(v[1]))
        })

        // 构建数据点（如果没有对应时间点的值，使用 null）
        const data = sortedTimes.map((time) => {
          const value = valueMap.get(time)
          return value !== undefined ? value : null
        })

        // 生成系列名称
        const seriesName = Object.keys(labels).length > 0
          ? Object.entries(labels)
              .map(([key, value]) => `${key}=${value}`)
              .join(', ')
          : `Series ${index + 1}`

        series.push({
          name: seriesName,
          type: 'line',
          data: data,
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: {
            width: 2
          }
        })
      })

      return {
        title: {
          text: '指标趋势',
          left: 'center',
          textStyle: {
            color: '#fff'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: (params: any) => {
            let result = `<div style="margin-bottom: 4px;">${params[0].axisValue}</div>`
            params.forEach((param: any) => {
              const value = param.value !== null ? param.value.toFixed(4) : 'N/A'
              result += `<div style="margin-top: 4px;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:${param.color};margin-right:5px;"></span>
                ${param.seriesName}: <strong>${value}</strong>
              </div>`
            })
            return result
          }
        },
        legend: {
          data: series.map(s => s.name),
          top: 30,
          textStyle: {
            color: '#fff'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '10%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: xAxisData,
          axisLabel: {
            color: '#999',
            rotate: 45
          },
          axisLine: {
            lineStyle: {
              color: '#666'
            }
          }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            color: '#999'
          },
          axisLine: {
            lineStyle: {
              color: '#666'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#333',
              type: 'dashed'
            }
          }
        },
        dataZoom: [
          {
            type: 'slider',
            show: true,
            xAxisIndex: [0],
            start: 0,
            end: 100,
            bottom: 20,
            textStyle: {
              color: '#999'
            }
          },
          {
            type: 'inside',
            xAxisIndex: [0],
            start: 0,
            end: 100
          }
        ],
        series: series
      }
    })

    // 日志检索
    const logForm = reactive({
      cluster_id: 0,
      query: '',
      range: defaultTimeRange as [Date, Date],
      limit: 100,
      page: 1,
      page_size: 100,
      highlight: true,
      stats: true
    })
    const logResult = ref<LogQueryResult | null>(null)

    const handleQueryLogs = async () => {
      if (!logForm.cluster_id) {
        ElMessage.warning('请选择集群')
        return
      }
      if (!logForm.query) {
        ElMessage.warning('请输入查询语句')
        return
      }
      try {
        const payload: Record<string, any> = {
          cluster_id: logForm.cluster_id,
          query: logForm.query,
          limit: logForm.limit,
          page: logForm.page,
          page_size: logForm.page_size,
          highlight: logForm.highlight,
          stats: logForm.stats
        }
        if (logForm.range && logForm.range.length === 2) {
          payload.start = logForm.range[0].toISOString()
          payload.end = logForm.range[1].toISOString()
        }
        const res = await queryLogs(payload as any)
        logResult.value = (res as any).data
        ElMessage.success('日志查询成功')
      } catch (error) {
        logResult.value = null
        if (!isAuthError(error)) {
          ElMessage.error('日志查询失败')
        }
      }
    }

    const resetLogForm = () => {
      logForm.query = ''
      logForm.page = 1
      logResult.value = null
    }

    // 诊断记录
    const diagnosisPagination = reactive({
      page: 1,
      size: 10,
      total: 0
    })
    const diagnosisList = ref<DiagnosisRecord[]>([])
    const diagnosisLoading = ref(false)

    // 诊断状态轮询
    let diagnosisPollTimer: number | null = null
    const DIAGNOSIS_POLL_INTERVAL = 3000 // 3秒轮询一次

    const startDiagnosisPolling = () => {
      // 如果已经有定时器在运行，先清除
      if (diagnosisPollTimer) {
        clearInterval(diagnosisPollTimer)
      }

      // 启动轮询
      diagnosisPollTimer = window.setInterval(() => {
        // 检查是否有正在进行的诊断任务
        const hasRunningDiagnosis = diagnosisList.value.some(
          (record) => ['pending', 'running', 'pending_next'].includes(record.status?.toLowerCase() || '')
        )

        if (hasRunningDiagnosis && activeTab.value === 'diagnosis') {
          // 静默刷新，不显示loading
          loadDiagnosis().catch(() => {
            // 静默失败
          })
        } else {
          // 没有进行中的诊断，停止轮询
          stopDiagnosisPolling()
        }
      }, DIAGNOSIS_POLL_INTERVAL)
    }

    const stopDiagnosisPolling = () => {
      if (diagnosisPollTimer) {
        clearInterval(diagnosisPollTimer)
        diagnosisPollTimer = null
      }
    }

    const loadDiagnosis = async () => {
      diagnosisLoading.value = true
      try {
        const res = await listDiagnosisRecords({
          page: diagnosisPagination.page,
          size: diagnosisPagination.size
        })
        const data = (res as any).data || {}
        diagnosisList.value = data.list ?? []
        diagnosisPagination.total = data.total ?? 0
      } catch (error) {
        diagnosisList.value = []
        diagnosisPagination.total = 0
        // 不再弹出错误，保持空态
      } finally {
        diagnosisLoading.value = false
      }
    }

    const createDiagnosisForm = () => ({
        cluster_id: 0,
      namespace: '',
        resource_type: 'pods',
        resource_name: '',
      time_range_hours: 2.0
    })

    const diagnosisDialog = reactive({
      visible: false,
      submitting: false,
      form: createDiagnosisForm()
    })

    const diagnosisNamespaces = ref<string[]>([])
    const diagnosisResources = ref<string[]>([])
    const diagnosisNamespaceLoading = ref(false)
    const diagnosisResourceLoading = ref(false)

    const ensureClusterSelection = () => {
      if (!clusters.value.length) return
      const exists = clusters.value.some((cluster) => cluster.id === diagnosisDialog.form.cluster_id)
      if (!exists) {
        diagnosisDialog.form.cluster_id = clusters.value[0].id
      }
    }

    const refreshDiagnosisOptions = async () => {
        await loadDiagnosisNamespaces()
            await loadDiagnosisResources()
          }

    const openManualDiagnosis = async () => {
      if (!clusters.value.length) {
        await loadClusters()
      }
      if (!clusters.value.length) {
        ElMessage.warning('请先添加集群配置')
        return
      }

      ensureClusterSelection()
      diagnosisDialog.form.resource_name = ''
      diagnosisDialog.visible = true
      await nextTick()
      await refreshDiagnosisOptions()
    }

    const loadDiagnosisNamespaces = async () => {
      const clusterId = diagnosisDialog.form.cluster_id
      if (!clusterId) {
        diagnosisNamespaces.value = []
        diagnosisDialog.form.namespace = ''
        return
      }
      diagnosisNamespaceLoading.value = true
      try {
        const res = await fetchClusterNamespaces(clusterId)
        const list = Array.isArray((res as any)?.data) ? (res as any).data : []
        diagnosisNamespaces.value = [...list]
        if (!list.length) {
          diagnosisDialog.form.namespace = ''
        } else if (!diagnosisDialog.form.namespace || !list.includes(diagnosisDialog.form.namespace)) {
          diagnosisDialog.form.namespace = list.includes('default') ? 'default' : list[0]
        }
      } catch (error) {
        console.error('[ERROR] loadDiagnosisNamespaces failed:', error)
        diagnosisNamespaces.value = []
        diagnosisDialog.form.namespace = ''
        if (!isAuthError(error)) {
          ElMessage.error('加载命名空间失败')
        }
      } finally {
        diagnosisNamespaceLoading.value = false
      }
    }

    const loadDiagnosisResources = async () => {
      const clusterId = diagnosisDialog.form.cluster_id
      const resourceType = diagnosisDialog.form.resource_type
      if (!clusterId || !resourceType) {
        diagnosisResources.value = []
        diagnosisDialog.form.resource_name = ''
        return
      }
      
      if (resourceType !== 'nodes' && !diagnosisDialog.form.namespace) {
        diagnosisResources.value = []
        diagnosisDialog.form.resource_name = ''
        return
      }
      
      diagnosisResourceLoading.value = true
      try {
        const params: Record<string, any> = {
          page: 1,
          size: 200,
          resource_type: resourceType
        }
        if (diagnosisDialog.form.namespace) {
          params.namespace = diagnosisDialog.form.namespace
        }
        const res = await fetchResourceSnapshots(clusterId, params as any)
        let list: ResourceSnapshot[] = []
        if ((res as any)?.data) {
          const resData = (res as any).data
          if (typeof resData === 'object' && !Array.isArray(resData)) {
            if (Array.isArray(resData.list)) {
              list = resData.list
            } else if (resData.list && Array.isArray(resData.list)) {
              list = resData.list
            }
          } else if (Array.isArray(resData)) {
            list = resData
          }
        }
        const names = Array.from(new Set(list.map((item: ResourceSnapshot) => item.resource_name).filter(Boolean)))
        diagnosisResources.value = [...names]
        if (diagnosisDialog.form.resource_name && !names.includes(diagnosisDialog.form.resource_name)) {
          diagnosisDialog.form.resource_name = names[0] || ''
        } else if (!diagnosisDialog.form.resource_name && names.length > 0) {
          diagnosisDialog.form.resource_name = names[0]
        }
      } catch (error) {
        console.error('[ERROR] loadDiagnosisResources failed:', error)
        diagnosisResources.value = []
        diagnosisDialog.form.resource_name = ''
        if (!isAuthError(error)) {
          ElMessage.error('加载资源列表失败')
        }
      } finally {
        diagnosisResourceLoading.value = false
      }
    }

    const submitManualDiagnosis = async () => {
      if (!diagnosisDialog.form.cluster_id) {
        ElMessage.warning('请选择集群')
        return
      }
      if (diagnosisDialog.form.resource_type !== 'nodes' && !diagnosisDialog.form.namespace) {
        ElMessage.warning('请选择命名空间')
        return
      }
      if (!diagnosisDialog.form.resource_name) {
        ElMessage.warning('请选择资源')
        return
      }

      diagnosisDialog.submitting = true
      try {
        await runDiagnosis({
          cluster_id: diagnosisDialog.form.cluster_id,
          namespace: diagnosisDialog.form.namespace || undefined,
          resource_type: diagnosisDialog.form.resource_type,
          resource_name: diagnosisDialog.form.resource_name,
          time_range_hours: diagnosisDialog.form.time_range_hours || 2.0
        })
        diagnosisDialog.visible = false
        ElMessage.success('诊断任务已触发，正在后台执行')

        if (activeTab.value !== 'diagnosis') {
          activeTab.value = 'diagnosis'
          await nextTick()
        }

        await loadDiagnosis()
        startDiagnosisPolling()

        ElNotification({
          title: '诊断已启动',
          message: `${diagnosisDialog.form.namespace || 'default'}/${diagnosisDialog.form.resource_name} 的诊断任务已开始执行`,
          type: 'info',
          duration: 5000
        })
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('诊断触发失败')
        }
      } finally {
        diagnosisDialog.submitting = false
      }
    }

    const handleDiagnosisClusterChange = async (value: number) => {
      diagnosisDialog.form.cluster_id = value
        diagnosisDialog.form.namespace = ''
        diagnosisDialog.form.resource_name = ''
      await refreshDiagnosisOptions()
    }

    const handleDiagnosisNamespaceChange = async (value: string) => {
      diagnosisDialog.form.namespace = value || ''
        diagnosisDialog.form.resource_name = ''
            await loadDiagnosisResources()
    }

    const handleDiagnosisResourceTypeChange = async (value: string) => {
      diagnosisDialog.form.resource_type = value || 'pods'
        diagnosisDialog.form.resource_name = ''
            await loadDiagnosisResources()
          }

    watch(
      () => diagnosisDialog.visible,
      (visible) => {
        if (!visible) {
          diagnosisDialog.submitting = false
          diagnosisNamespaces.value = []
          diagnosisResources.value = []
          Object.assign(diagnosisDialog.form, createDiagnosisForm())
        }
      }
    )

    const diagnosisDrawer = reactive<{
      visible: boolean
      record: DiagnosisRecord | null
    }>({
      visible: false,
      record: null
    })

    const diagnosisUpdatedAt = computed(() => {
      if (!diagnosisDrawer.record) return ''
      const timestamp = diagnosisDrawer.record.updated_at || diagnosisDrawer.record.created_at
      return timestamp ? formatDateTime(timestamp) : ''
    })

    const diagnosisConfidencePercent = computed(() => {
      if (!diagnosisDrawer.record || diagnosisDrawer.record.confidence == null) return null
      return Math.round((diagnosisDrawer.record.confidence || 0) * 100)
    })

    const diagnosisConfidenceStatus = computed(() => {
      if (!diagnosisDrawer.record || diagnosisDrawer.record.confidence == null) return 'warning'
      const value = diagnosisDrawer.record.confidence
      if (value > 0.7) return 'success'
      if (value > 0.4) return 'warning'
      return 'exception'
    })

    const feedbackForm = reactive<SubmitDiagnosisFeedbackPayload>({
      feedback_type: 'confirmed',
      feedback_notes: '',
      action_taken: '',
      iteration_no: undefined
    })

    const requiresFeedbackNotes = computed(
      () => feedbackForm.feedback_type === 'continue_investigation' || feedbackForm.feedback_type === 'custom'
    )

    const feedbackNotesPlaceholder = computed(() => {
      if (feedbackForm.feedback_type === 'continue_investigation') {
        return '请描述为什么需要继续排查、缺失哪些信息、希望系统补充什么'
      }
      if (feedbackForm.feedback_type === 'custom') {
        return '请输入详细的反馈说明，便于后续跟进'
      }
      return '可选，如：已确认是配置变更导致，可沉淀为知识库案例'
    })

    const getLatestIterationNo = (iterations?: DiagnosisIteration[]): number | undefined => {
      if (!iterations || iterations.length === 0) return undefined
      return iterations[iterations.length - 1].iteration_no
    }

    const resetFeedbackForm = (record?: DiagnosisRecord | null, fallbackIterations?: DiagnosisIteration[]) => {
      feedbackForm.feedback_type = 'confirmed'
      feedbackForm.feedback_notes = ''
      feedbackForm.action_taken = ''
      feedbackForm.iteration_no = getLatestIterationNo(record?.iterations || fallbackIterations)
    }

    const syncFeedbackIterationSelection = (iterations?: DiagnosisIteration[] | null) => {
      if (!iterations || iterations.length === 0) {
        feedbackForm.iteration_no = undefined
        return
      }
      const exists = feedbackForm.iteration_no
        ? iterations.some((item) => item.iteration_no === feedbackForm.iteration_no)
        : false
      if (!exists) {
        feedbackForm.iteration_no = iterations[iterations.length - 1].iteration_no
      }
    }

    const iterationTimeline = ref<DiagnosisIteration[]>([])
    const memoryTimeline = ref<DiagnosisMemory[]>([])
    const iterationLoading = ref(false)
    const memoryLoading = ref(false)
    const diagnosisReport = ref<any>(null)

    const feedbackOptions = FEEDBACK_OPTIONS

    const iterationOptions = computed(() => {
      const source = iterationTimeline.value.length
        ? iterationTimeline.value
        : diagnosisDrawer.record?.iterations || []
      return source.map((item) => ({
        label: `第 ${item.iteration_no} 轮`,
        value: item.iteration_no
      }))
    })

    const feedbackState = computed<DiagnosisFeedbackState | null>(() => {
      const feedback = diagnosisDrawer.record?.feedback as { state?: DiagnosisFeedbackState } | undefined
      return feedback?.state || null
    })

    const feedbackLatest = computed<DiagnosisFeedbackEntry | null>(() => {
      const feedback = diagnosisDrawer.record?.feedback as { latest?: DiagnosisFeedbackEntry } | undefined
      return feedback?.latest || null
    })

    const formatFeedbackType = (type?: string) => {
      switch (type) {
        case 'confirmed':
          return '已确认根因'
        case 'continue_investigation':
          return '继续排查'
        case 'custom':
          return '其他反馈'
        default:
          return '未知'
      }
    }

    const feedbackStateDescription = computed(() => {
      if (!feedbackState.value) return ''
      const state = feedbackState.value
      if (state.last_feedback_type === 'continue_investigation') {
        const lastIteration = state.last_feedback_iteration ?? '-'
        const nextIterationLabel =
          typeof state.last_feedback_iteration === 'number' && !Number.isNaN(state.last_feedback_iteration)
            ? `第${state.last_feedback_iteration + 1}轮`
            : '下一轮'
        const continueStep = state.continue_from_step ?? 1
        const minStep = state.min_steps_before_exit ?? 3
        return `上一轮（第${lastIteration}轮）在第 ${continueStep} 步结束并要求继续排查，因此本轮（${nextIterationLabel}）必须至少执行到第 ${minStep} 步后才能结束。`
      }
      if (state.last_feedback_type === 'confirmed') {
        return `上一轮（第${state.last_feedback_iteration ?? '-'}轮）已确认当前诊断结论。`
      }
      return ''
    })

    const loadIterationTimeline = async (recordId: number) => {
      iterationLoading.value = true
      try {
        const res = await listDiagnosisIterations(recordId)
        iterationTimeline.value = (res as any).data?.list ?? []
        syncFeedbackIterationSelection(iterationTimeline.value)
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('加载迭代历史失败')
        } else {
          iterationTimeline.value = []
          syncFeedbackIterationSelection([])
        }
      } finally {
        iterationLoading.value = false
      }
    }

    const loadMemoryTimeline = async (recordId: number) => {
      memoryLoading.value = true
      try {
        const res = await listDiagnosisMemories(recordId)
        memoryTimeline.value = (res as any).data?.list ?? []
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('加载上下文记忆失败')
        } else {
          memoryTimeline.value = []
        }
      } finally {
        memoryLoading.value = false
      }
    }

    const loadDiagnosisReport = async (recordId: number) => {
      try {
        const res = await getDiagnosisReport(recordId)
        diagnosisReport.value = res.data
      } catch (error) {
        if (!isAuthError(error)) {
          // 静默失败，报告可能不存在
          diagnosisReport.value = null
        }
      }
    }

    const openDiagnosisDetail = async (record: DiagnosisRecord) => {
      diagnosisDrawer.visible = true
      diagnosisDrawer.record = record
      resetFeedbackForm(record)

      let targetRecord: DiagnosisRecord | null = record
      // 调用API获取完整的诊断记录详情（符合设计文档要求）
      try {
        const res = await getDiagnosisRecord(record.id)
        diagnosisDrawer.record = (res as any).data
        targetRecord = (res as any).data
        
        // 如果 symptoms 是字符串，尝试解析
        if (targetRecord?.symptoms && typeof targetRecord.symptoms === 'string') {
          try {
            targetRecord.symptoms = JSON.parse(targetRecord.symptoms)
            diagnosisDrawer.record = targetRecord
          } catch (e) {
            // 解析失败，保持原样
          }
        }
      } catch (error) {
        console.error('[ERROR] getDiagnosisRecord failed:', error)
        if (!isAuthError(error)) {
          ElMessage.error('获取诊断详情失败')
        }
        diagnosisDrawer.record = record
        targetRecord = record
      }

      resetFeedbackForm(targetRecord)

      // 加载迭代历史和记忆
      if (targetRecord) {
        loadIterationTimeline(targetRecord.id)
        loadMemoryTimeline(targetRecord.id)
        if (targetRecord.status === 'pending_human') {
          loadDiagnosisReport(targetRecord.id)
        }
      }
    }
    const submitFeedback = async () => {
      if (!diagnosisDrawer.record) return
      if (!feedbackForm.feedback_type) {
        ElMessage.warning('请选择反馈类型')
        return
      }
      if (requiresFeedbackNotes.value && !feedbackForm.feedback_notes?.trim()) {
        ElMessage.warning('请填写反馈说明')
        return
      }

      const payload: SubmitDiagnosisFeedbackPayload = {
        feedback_type: feedbackForm.feedback_type,
        feedback_notes: feedbackForm.feedback_notes?.trim() || undefined,
        action_taken: feedbackForm.action_taken?.trim() || undefined,
        iteration_no: feedbackForm.iteration_no
      }

      try {
        const res = await submitDiagnosisFeedback(diagnosisDrawer.record.id, payload)
        const resData = (res as any).data
        diagnosisDrawer.record = resData
        resetFeedbackForm(resData)
        const tip =
          payload.feedback_type === 'continue_investigation'
            ? '反馈已提交，已启动新的诊断迭代'
            : payload.feedback_type === 'confirmed'
              ? '反馈已提交，已沉淀到知识库'
              : '反馈已提交'
        ElMessage.success(tip)
        loadDiagnosis()
        loadIterationTimeline(resData.id)
        loadMemoryTimeline(resData.id)
        if (resData.status === 'pending_human') {
          loadDiagnosisReport(resData.id)
        }
      } catch (error) {
        if (!isAuthError(error)) {
          ElMessage.error('反馈提交失败')
        }
      }
    }

    const handleDeleteDiagnosis = async (record: DiagnosisRecord) => {
      try {
        await ElMessageBox.confirm(`确认删除诊断记录【${record.resource_name}】吗？`, '提示', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        })
        await deleteDiagnosisRecord(record.id)
        ElMessage.success('删除成功')
        if (diagnosisDrawer.visible && diagnosisDrawer.record?.id === record.id) {
          diagnosisDrawer.visible = false
          diagnosisDrawer.record = null
        }
        await loadDiagnosis()
      } catch (error: any) {
        if (error === 'cancel' || error === 'close') {
          return
        }
        if (!isAuthError(error)) {
          ElMessage.error('删除失败')
        }
      }
    }

    const handleDeleteDiagnosisFromDetail = async () => {
      if (!diagnosisDrawer.record) return
      await handleDeleteDiagnosis(diagnosisDrawer.record)
    }

    // 公共方法
    const handleTabChange = (tab: string) => {
      if (tab === 'resources') {
        loadResources()
      } else if (tab === 'metrics' && metricsResult.value === null) {
        metricsForm.cluster_id = metricsForm.cluster_id || clusters.value[0]?.id || 0
      } else if (tab === 'logs') {
        logForm.cluster_id = logForm.cluster_id || clusters.value[0]?.id || 0
      } else if (tab === 'diagnosis') {
        loadDiagnosis()
        // 检查是否有进行中的诊断
        nextTick(() => {
          const hasRunningDiagnosis = diagnosisList.value.some(
            (record) => ['pending', 'running', 'pending_next'].includes(record.status?.toLowerCase() || '')
          )
          if (hasRunningDiagnosis) {
            startDiagnosisPolling()
          }
        })
      } else {
        // 切换到其他标签时，停止轮询
        stopDiagnosisPolling()
      }
    }

    const stringify = (value: any) => {
      if (!value) return '-'
      try {
        return JSON.stringify(value, null, 2)
      } catch {
        return String(value)
      }
    }

    // 获取所有证据链数据（合并 evidence_chain 和直接的 record 字段）
    const getAllEvidenceChain = (record: DiagnosisRecord | null) => {
      if (!record) return {}
      
      const rootCauseData = getRootCauseAnalysis(record)
      const evidenceChain = rootCauseData?.evidence_chain || {}
      const result: any = { ...evidenceChain }
      
      // 如果 evidence_chain 中没有 logs，尝试从 record.logs 获取
      if (!result.logs || (Array.isArray(result.logs) && result.logs.length === 0)) {
        try {
          let logsData: any = record.logs
          if (typeof logsData === 'string') {
            try {
              logsData = JSON.parse(logsData)
            } catch {
              result.logs = [logsData]
              logsData = null
            }
          }
          
          if (logsData) {
            if (Array.isArray(logsData)) {
              result.logs = logsData.filter((item: any) => item != null)
            } else if (typeof logsData === 'object') {
              const logsObj = logsData as any
              // 优先从 logs 字段获取（后端返回的格式）
              if (logsObj.logs && Array.isArray(logsObj.logs)) {
                result.logs = logsObj.logs.filter((item: any) => item != null)
              } else if (logsObj.entries && Array.isArray(logsObj.entries)) {
                result.logs = logsObj.entries.filter((item: any) => item != null)
              } else if (logsObj.results && Array.isArray(logsObj.results)) {
                result.logs = logsObj.results.filter((item: any) => item != null)
              }
            }
          }
          
        } catch (error) {
          // 提取日志信息失败，忽略错误
        }
      }
      
      // 如果 evidence_chain 中没有 metrics，尝试从 record.metrics 获取
      if (!result.metrics && record.metrics) {
        try {
          let metricsData: any = record.metrics
          if (typeof metricsData === 'string') {
            try {
              metricsData = JSON.parse(metricsData)
            } catch {
              metricsData = null
            }
          }
          
          if (metricsData && typeof metricsData === 'object' && !Array.isArray(metricsData)) {
            const filteredMetrics: any = {}
            Object.keys(metricsData).forEach(key => {
              const value = metricsData[key]
              if (value != null && value !== '' && value !== undefined) {
                filteredMetrics[key] = value
              }
            })
            if (Object.keys(filteredMetrics).length > 0) {
              result.metrics = filteredMetrics
            }
          }
        } catch (error) {
          // 忽略错误
        }
      }
      
      // 如果 evidence_chain 中没有 events，尝试从 record.events 获取
      if (!result.events && record.events) {
        try {
          let eventsData: any = record.events
          if (typeof eventsData === 'string') {
            try {
              eventsData = JSON.parse(eventsData)
            } catch {
              eventsData = null
            }
          }
          
          if (eventsData) {
            if (Array.isArray(eventsData) && eventsData.length > 0) {
              result.events = eventsData.map((event: any) => {
                if (typeof event === 'string') {
                  return { message: event }
                }
                return event
              }).filter((item: any) => item != null)
            } else if (typeof eventsData === 'object' && !Array.isArray(eventsData)) {
              const eventsObj = eventsData as any
              if (eventsObj.events && Array.isArray(eventsObj.events)) {
                result.events = eventsObj.events
              } else if (eventsObj.list && Array.isArray(eventsObj.list)) {
                result.events = eventsObj.list
              }
            }
          }
        } catch (error) {
          // 忽略错误
        }
      }
      
      // 如果 evidence_chain 中没有 config 或 config 为空对象，尝试从 symptoms 或 record 中获取
      const hasConfig = result.config && typeof result.config === 'object' && !Array.isArray(result.config) && Object.keys(result.config).length > 0
      
      if (!hasConfig) {
        try {
          const symptoms = record.symptoms as any
          if (symptoms) {
            // 如果 symptoms 是字符串，尝试解析
            let symptomsObj: any = symptoms
            if (typeof symptoms === 'string') {
              try {
                symptomsObj = JSON.parse(symptoms)
              } catch {
                symptomsObj = null
              }
            }
            
            if (symptomsObj) {
              // 优先从 symptoms.config 获取
              if (symptomsObj.config) {
                let configData: any = symptomsObj.config
                // 如果 config 是字符串，尝试解析
                if (typeof configData === 'string') {
                  try {
                    configData = JSON.parse(configData)
                  } catch {
                    // 解析失败，忽略
                  }
                }
                
                if (configData && typeof configData === 'object' && !Array.isArray(configData) && Object.keys(configData).length > 0) {
                  result.config = configData
                }
              } else if (symptomsObj.configuration && typeof symptomsObj.configuration === 'object' && !Array.isArray(symptomsObj.configuration) && Object.keys(symptomsObj.configuration).length > 0) {
                result.config = symptomsObj.configuration
              }
            }
          }
          
          // 如果 symptoms 中没有，尝试从 record 的 config 字段获取
          if ((!result.config || (typeof result.config === 'object' && !Array.isArray(result.config) && Object.keys(result.config).length === 0)) && (record as any).config) {
            let configData: any = (record as any).config
            if (typeof configData === 'string') {
              try {
                configData = JSON.parse(configData)
              } catch {
                configData = null
              }
            }
            if (configData && typeof configData === 'object' && !Array.isArray(configData) && Object.keys(configData).length > 0) {
              result.config = configData
            }
          }
        } catch (error) {
          // 提取配置信息失败，忽略错误
        }
      }
      
      // 过滤掉空值（但保留 config，即使它可能被误判为空）
      Object.keys(result).forEach(key => {
        const value = result[key]
        // 对于 config，需要特殊处理：如果它是从 symptoms.config 提取的，即使看起来是空对象也要保留
        if (key === 'config' && value && typeof value === 'object' && !Array.isArray(value)) {
          // 检查 symptoms.config 是否存在且有数据
          const symptoms = record.symptoms as any
          if (symptoms?.config && typeof symptoms.config === 'object' && Object.keys(symptoms.config).length > 0) {
            // 如果 symptoms.config 有数据，确保 result.config 使用它
            result.config = symptoms.config
            return // 不删除 config
          }
        }
        
        if (!value || 
            (Array.isArray(value) && value.length === 0) ||
            (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) ||
            value === null || value === undefined) {
          delete result[key]
        }
      })
      
      // 最后再次确保 config 存在（如果 symptoms.config 有数据）
      // 重新获取 symptoms（可能在前面被修改过）
      let finalSymptoms: any = record.symptoms
      if (typeof finalSymptoms === 'string') {
        try {
          finalSymptoms = JSON.parse(finalSymptoms)
        } catch {
          finalSymptoms = null
        }
      }
      
      if (finalSymptoms?.config) {
        let finalConfig: any = finalSymptoms.config
        if (typeof finalConfig === 'string') {
          try {
            finalConfig = JSON.parse(finalConfig)
          } catch {
            finalConfig = null
          }
        }
        
        if (finalConfig && typeof finalConfig === 'object' && !Array.isArray(finalConfig) && Object.keys(finalConfig).length > 0) {
          // 无论 result.config 是否存在或为空，都使用 symptoms.config（因为后端已经提取并存储在这里）
          result.config = finalConfig
        }
      }
      
      // 最后强制确保 config 存在（无论之前的逻辑如何，只要 symptoms.config 有数据就添加）
      const forceCheckSymptoms: any = record.symptoms
      let parsedSymptoms: any = forceCheckSymptoms
      
      // 如果 symptoms 是字符串，先解析
      if (typeof forceCheckSymptoms === 'string') {
        try {
          parsedSymptoms = JSON.parse(forceCheckSymptoms)
        } catch {
          parsedSymptoms = null
        }
      }
      
      if (parsedSymptoms?.config) {
        let forceConfig: any = parsedSymptoms.config
        
        // 如果 config 是字符串，尝试解析
        if (typeof forceConfig === 'string') {
          try {
            forceConfig = JSON.parse(forceConfig)
          } catch {
            forceConfig = null
          }
        }
        
        // 无论 result.config 是否存在或为空，都使用 symptoms.config
        if (forceConfig && typeof forceConfig === 'object' && !Array.isArray(forceConfig) && Object.keys(forceConfig).length > 0) {
          result.config = forceConfig
        }
      }
      
      return result
    }

    // 提取根因分析数据
    const getRootCauseAnalysis = (record: DiagnosisRecord | null) => {
      if (!record) return null

      const symptoms = record.symptoms as any
      const llmResult = record.recommendations as any
      const report = diagnosisReport.value?.report
      
      // 尝试从多个数据源提取证据链
      let evidenceChain: any = {}
      let rootCause = null
      let rootCauseAnalysis = null
      
      // 1. 优先从诊断报告中获取
      if (report) {
        rootCause = rootCause || report.root_cause
        rootCauseAnalysis = rootCauseAnalysis || report.root_cause_analysis
        if (report.evidence_chain && typeof report.evidence_chain === 'object') {
          evidenceChain = { ...evidenceChain, ...report.evidence_chain }
        }
      }
      
      // 2. 从 llm_result 获取
      if (llmResult?.latest?.llm_result) {
        const llmData = llmResult.latest.llm_result
        rootCause = rootCause || llmData.root_cause
        rootCauseAnalysis = rootCauseAnalysis || llmData.root_cause_analysis
        if (llmData.evidence_chain && typeof llmData.evidence_chain === 'object') {
          evidenceChain = { ...evidenceChain, ...llmData.evidence_chain }
        }
      }
      
      // 3. 从 symptoms 中获取
      if (symptoms) {
        rootCause = rootCause || symptoms.root_cause
        rootCauseAnalysis = rootCauseAnalysis || symptoms.root_cause_analysis
        if (symptoms.evidence_chain && typeof symptoms.evidence_chain === 'object') {
          evidenceChain = { ...evidenceChain, ...symptoms.evidence_chain }
        }
      }
      
      // 4. 从诊断记录的直接字段中提取证据链（logs, metrics, events）- 作为补充
      // 从 record.logs 提取日志
      if (record.logs && !evidenceChain.logs) {
        try {
          let logsData: any = record.logs
          // 如果是字符串，尝试解析
          if (typeof logsData === 'string') {
            try {
              logsData = JSON.parse(logsData)
            } catch {
              // 解析失败，当作普通字符串
              evidenceChain.logs = [logsData]
              logsData = null
            }
          }
          
          if (logsData) {
            if (Array.isArray(logsData)) {
              evidenceChain.logs = logsData.filter((item: any) => item != null)
            } else if (typeof logsData === 'object') {
              const logsObj = logsData as any
              if (logsObj.logs && Array.isArray(logsObj.logs)) {
                evidenceChain.logs = logsObj.logs.filter((item: any) => item != null)
              } else if (logsObj.entries && Array.isArray(logsObj.entries)) {
                evidenceChain.logs = logsObj.entries.filter((item: any) => item != null)
              } else if (logsObj.content && Array.isArray(logsObj.content)) {
                evidenceChain.logs = logsObj.content.filter((item: any) => item != null)
              } else if (logsObj.results && Array.isArray(logsObj.results)) {
                evidenceChain.logs = logsObj.results.filter((item: any) => item != null)
              } else {
                // 如果整个对象就是日志数据，尝试提取所有值
                const logEntries = Object.values(logsObj).filter((v: any) => v != null)
                if (logEntries.length > 0) {
                  evidenceChain.logs = logEntries.map((v: any) => {
                    if (typeof v === 'string') return v
                    if (typeof v === 'object' && v.message) return v.message
                    return stringify(v)
                  }).filter((v: any) => v && v.trim && v.trim().length > 0)
                }
              }
            }
          }
        } catch (error) {
          // 忽略错误，继续处理其他数据
        }
      }
      
      // 从 record.metrics 提取指标
      if (record.metrics && !evidenceChain.metrics) {
        try {
          let metricsData: any = record.metrics
          // 如果是字符串，尝试解析
          if (typeof metricsData === 'string') {
            try {
              metricsData = JSON.parse(metricsData)
            } catch {
              metricsData = null
            }
          }
          
          if (metricsData && typeof metricsData === 'object' && !Array.isArray(metricsData)) {
            const metricsObj = metricsData as any
            // 过滤掉空值
            const filteredMetrics: any = {}
            Object.keys(metricsObj).forEach(key => {
              const value = metricsObj[key]
              if (value != null && value !== '' && value !== undefined) {
                // 如果是对象或数组，直接赋值；如果是基本类型，也赋值
                filteredMetrics[key] = value
              }
            })
            if (Object.keys(filteredMetrics).length > 0) {
              evidenceChain.metrics = filteredMetrics
            }
          }
        } catch (error) {
          // 忽略错误，继续处理其他数据
        }
      }
      
      // 从 record.events 提取事件
      if (record.events && !evidenceChain.events) {
        try {
          let eventsData: any = record.events
          // 如果是字符串，尝试解析
          if (typeof eventsData === 'string') {
            try {
              eventsData = JSON.parse(eventsData)
            } catch {
              eventsData = null
            }
          }
          
          if (eventsData) {
            if (Array.isArray(eventsData) && eventsData.length > 0) {
              evidenceChain.events = eventsData.map((event: any) => {
                if (typeof event === 'string') {
                  return { message: event }
                }
                return event
              }).filter((item: any) => item != null)
            } else if (typeof eventsData === 'object' && !Array.isArray(eventsData)) {
              const eventsObj = eventsData as any
              if (eventsObj.events && Array.isArray(eventsObj.events)) {
                evidenceChain.events = eventsObj.events
              } else if (eventsObj.list && Array.isArray(eventsObj.list)) {
                evidenceChain.events = eventsObj.list
              } else {
                // 尝试将对象转换为事件数组
                const eventValues = Object.values(eventsObj).filter((v: any) => v != null)
                if (eventValues.length > 0) {
                  evidenceChain.events = eventValues.map((v: any) => {
                    if (typeof v === 'string') return { message: v }
                    return v
                  })
                }
              }
            }
          }
        } catch (error) {
          // 忽略错误，继续处理其他数据
        }
      }
      
      // 从 symptoms 中提取配置信息（如果 evidence_chain 中没有 config 或 config 为空对象）
      if (symptoms && (!evidenceChain.config || (typeof evidenceChain.config === 'object' && !Array.isArray(evidenceChain.config) && Object.keys(evidenceChain.config).length === 0))) {
        try {
          if (symptoms.config && typeof symptoms.config === 'object' && Object.keys(symptoms.config).length > 0) {
            evidenceChain.config = symptoms.config
          } else if (symptoms.configuration && typeof symptoms.configuration === 'object' && Object.keys(symptoms.configuration).length > 0) {
            evidenceChain.config = symptoms.configuration
          } else if ((record as any).config && typeof (record as any).config === 'object' && Object.keys((record as any).config).length > 0) {
            evidenceChain.config = (record as any).config
          }
        } catch (error) {
          // 忽略错误
        }
      }
      
      // 5. 尝试从迭代历史中提取证据链（从 action_result 中）- 作为最后补充
      if (iterationTimeline.value.length > 0) {
        const latestIteration = iterationTimeline.value[0]
        if (latestIteration?.action_result) {
          const actionResult = latestIteration.action_result
          if (Array.isArray(actionResult)) {
            const collectDataAction = actionResult.find((item: any) => item.name === 'collect_data')
            if (collectDataAction?.details) {
              const details = collectDataAction.details
              // 补充缺失的证据链数据
              if (details.logs && !evidenceChain.logs) {
                evidenceChain.logs = Array.isArray(details.logs) ? details.logs : (typeof details.logs === 'number' ? [] : [details.logs])
              }
              if (details.metrics && !evidenceChain.metrics) {
                evidenceChain.metrics = details.metrics
              }
              if (details.config && (!evidenceChain.config || (typeof evidenceChain.config === 'object' && !Array.isArray(evidenceChain.config) && Object.keys(evidenceChain.config).length === 0))) {
                evidenceChain.config = details.config
              }
              if (details.events && !evidenceChain.events) {
                evidenceChain.events = Array.isArray(details.events) ? details.events : [details.events]
              }
            }
          }
        }
      }
      
      // 过滤掉空值
      if (evidenceChain && Object.keys(evidenceChain).length > 0) {
        Object.keys(evidenceChain).forEach(key => {
          const value = evidenceChain[key]
          if (!value || 
              (Array.isArray(value) && value.length === 0) ||
              (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) ||
              value === null || value === undefined) {
            delete evidenceChain[key]
          }
        })
        if (Object.keys(evidenceChain).length === 0) {
          evidenceChain = null
        }
      } else {
        evidenceChain = null
      }
      
      // 如果有任何数据，返回结果
      if (rootCause || rootCauseAnalysis || evidenceChain) {
        return {
          root_cause: rootCause,
          root_cause_analysis: rootCauseAnalysis,
          evidence_chain: evidenceChain
        }
      }

      return null
    }

    // 提取 5 Why 步骤
    const getWhySteps = (rootCauseAnalysis: any): string[] => {
      if (!rootCauseAnalysis) return []
      const steps: string[] = []
      for (let i = 1; i <= 5; i++) {
        const why = rootCauseAnalysis[`why${i}`]
        if (why) {
          steps.push(why)
        }
      }
      return steps
    }

    // 提取时间线数据
    const getTimeline = (record: DiagnosisRecord | null) => {
      if (!record) return null
      
      let timeline: any = null
      
      // 1. 优先从 symptoms 中获取
      const symptoms = record.symptoms as any
      if (symptoms?.timeline) {
        timeline = symptoms.timeline
      }
      
      // 2. 如果没有，从 llm_result 中获取
      if (!timeline) {
      const llmResult = record.recommendations as any
      if (llmResult?.latest?.llm_result?.timeline) {
          timeline = llmResult.latest.llm_result.timeline
        }
      }
      
      // 获取记录的实际时间字段作为回退
      const recordStartTime = record.started_at || record.created_at
      const recordEscalateTime = record.completed_at || record.updated_at || record.started_at || record.created_at
      
      // 检查时间是否合理的辅助函数（检查年份是否合理，2025年及之后）
      const isValidTime = (timeStr: string | null | undefined): boolean => {
        if (!timeStr) return false
        try {
          const time = new Date(timeStr)
          const year = time.getFullYear()
          // 检查年份是否在合理范围内（2024年之后，或者至少是记录创建时间之后）
          return year >= 2024
        } catch {
          return false
        }
      }
      
      // 3. 如果没有时间线数据，使用 record 的时间字段创建默认时间线
      if (!timeline) {
        timeline = {
          problem_start: recordStartTime,
          problem_escalate: recordEscalateTime,
          key_events: []
        }
      } else {
        // 4. 如果时间线数据存在但时间字段为空或无效（年份太旧），使用 record 的时间字段作为回退
        if (!timeline.problem_start || !isValidTime(timeline.problem_start)) {
          timeline.problem_start = recordStartTime
        }
        if (!timeline.problem_escalate || !isValidTime(timeline.problem_escalate)) {
          timeline.problem_escalate = recordEscalateTime
        }
      }
      
      return timeline
    }

    // 提取影响范围数据
    const getImpactScope = (record: DiagnosisRecord | null) => {
      if (!record) return null
      const symptoms = record.symptoms as any
      if (symptoms?.impact_scope) {
        return symptoms.impact_scope
      }
      const llmResult = record.recommendations as any
      if (llmResult?.latest?.llm_result?.impact_scope) {
        return llmResult.latest.llm_result.impact_scope
      }
      return null
    }

    // 提取结构化解决方案
    const getStructuredSolutions = (record: DiagnosisRecord | null) => {
      if (!record) return null
      const recommendations = record.recommendations as any
      if (recommendations?.solutions) {
        return recommendations.solutions
      }
      const llmResult = recommendations?.latest?.llm_result
      if (llmResult?.solutions) {
        return llmResult.solutions
      }
      return null
    }

    const renderHighlight = (highlight: string | string[]) => {
      if (Array.isArray(highlight)) {
        return highlight.join('<br>')
      }
      return highlight
    }

    // 证据链辅助方法
    const getEvidenceIcon = (key: string) => {
      const keyLower = key.toLowerCase()
      if (keyLower === 'logs') return 'Document'
      if (keyLower === 'config') return 'Setting'
      if (keyLower === 'events') return 'Bell'
      if (keyLower === 'metrics') return 'DataAnalysis'
      return 'InfoFilled'
    }

    const getEvidenceTitle = (key: string) => {
      const keyLower = key.toLowerCase()
      const titleMap: Record<string, string> = {
        logs: '日志信息',
        config: '配置信息',
        events: '事件信息',
        metrics: '指标信息'
      }
      return titleMap[keyLower] || key
    }

    const isErrorLog = (item: any): boolean => {
      if (typeof item === 'string') {
        const lower = item.toLowerCase()
        return lower.includes('error') || 
               lower.includes('failed') || 
               lower.includes('exception') || 
               lower.includes('oom') ||
               lower.includes('killed')
      }
      if (item && typeof item === 'object') {
        const str = stringify(item).toLowerCase()
        return str.includes('error') || 
               str.includes('failed') || 
               str.includes('exception') ||
               str.includes('oom') ||
               str.includes('killed')
      }
      return false
    }

    const formatConfigValue = (value: any): string => {
      if (value === null || value === undefined) return '-'
      if (typeof value === 'object') {
        return stringify(value)
      }
      return String(value)
    }

    const getEventIcon = (item: any) => {
      if (typeof item === 'string') {
        const lower = item.toLowerCase()
        if (lower.includes('error') || lower.includes('failed') || lower.includes('killed')) {
          return 'CircleCloseFilled'
        }
        if (lower.includes('success') || lower.includes('started') || lower.includes('completed')) {
          return 'CircleCheckFilled'
        }
      }
      if (item && typeof item === 'object') {
        const str = stringify(item).toLowerCase()
        if (str.includes('error') || str.includes('failed') || str.includes('killed')) {
          return 'CircleCloseFilled'
        }
        if (str.includes('success') || str.includes('started') || str.includes('completed')) {
          return 'CircleCheckFilled'
        }
      }
      return 'InfoFilled'
    }

    const getEventIconClass = (item: any) => {
      const icon = getEventIcon(item)
      if (icon === 'CircleCloseFilled') return 'event-icon-error'
      if (icon === 'CircleCheckFilled') return 'event-icon-success'
      return 'event-icon-info'
    }

    const getEventAlertType = (item: any): 'error' | 'success' | 'warning' | 'info' => {
      if (typeof item === 'string') {
        const lower = item.toLowerCase()
        if (lower.includes('error') || lower.includes('failed') || lower.includes('killed') || lower.includes('oom')) {
          return 'error'
        }
        if (lower.includes('success') || lower.includes('started') || lower.includes('completed')) {
          return 'success'
        }
        if (lower.includes('warning') || lower.includes('warn')) {
          return 'warning'
        }
      }
      if (item && typeof item === 'object') {
        const str = stringify(item).toLowerCase()
        if (str.includes('error') || str.includes('failed') || str.includes('killed') || str.includes('oom')) {
          return 'error'
        }
        if (str.includes('success') || str.includes('started') || str.includes('completed')) {
          return 'success'
        }
        if (str.includes('warning') || str.includes('warn')) {
          return 'warning'
        }
      }
      return 'info'
    }

    const getEventAlertClass = (item: any): string => {
      const type = getEventAlertType(item)
      return `event-alert-${type}`
    }

    const formatMetricValue = (value: any): string => {
      if (value === null || value === undefined) return '-'
      if (typeof value === 'number') {
        // 如果是百分比，显示百分比
        if (value > 0 && value <= 1) {
          return `${(value * 100).toFixed(2)}%`
        }
        // 如果是大数字，格式化
        if (value >= 1000) {
          return value.toLocaleString()
        }
        return value.toString()
      }
      return String(value)
    }

    const getMetricValueClass = (value: any): string => {
      if (typeof value === 'number') {
        // 如果是百分比
        if (value > 0 && value <= 1) {
          if (value > 0.8) return 'metric-value-danger'
          if (value > 0.6) return 'metric-value-warning'
          return 'metric-value-success'
        }
        // 如果是内存值（Mi）
        if (String(value).includes('Mi') || String(value).includes('Gi')) {
          return 'metric-value-info'
        }
      }
      return 'metric-value-info'
    }

    watch(
      () => diagnosisDrawer.visible,
      (visible) => {
        if (!visible) {
          iterationTimeline.value = []
          memoryTimeline.value = []
          diagnosisReport.value = null
        }
      }
    )

    const copyRaw = async (payload: any) => {
      try {
        await navigator.clipboard.writeText(stringify(payload))
        ElMessage.success('已复制到剪贴板')
      } catch {
        ElMessage.error('复制失败')
      }
    }

    const healthStatusTagType = (status?: string) => {
      switch ((status || '').toLowerCase()) {
        case 'ok':
        case 'healthy':
          return 'success'
        case 'warning':
          return 'warning'
        case 'error':
        case 'unhealthy':
          return 'danger'
        default:
          return 'info'
      }
    }

    const eventTagType = (type: string) => {
      switch (type) {
        case 'created':
          return 'success'
        case 'updated':
          return 'warning'
        case 'deleted':
          return 'danger'
        default:
          return 'info'
      }
    }

    const logLevelTagType = (level?: string) => {
      const normalized = (level || '').toLowerCase()
      if (['error', 'err', 'critical', 'fatal'].includes(normalized)) return 'danger'
      if (['warn', 'warning'].includes(normalized)) return 'warning'
      if (['info', 'notice'].includes(normalized)) return 'info'
      if (['debug', 'trace'].includes(normalized)) return 'success'
      return 'default'
    }

    const diagnosisStatusTag = (status: string) => {
      switch ((status || '').toLowerCase()) {
        case 'completed':
          return 'success'
        case 'running':
          return 'warning'
        case 'pending_next':
          return 'warning'
        case 'pending_human':
          return 'info'
        case 'failed':
          return 'danger'
        default:
          return 'info'
      }
    }

    const formatDiagnoseStatus = (status: string) => {
      switch ((status || '').toLowerCase()) {
        case 'completed':
          return '已完成'
        case 'running':
          return '诊断中'
        case 'pending_next':
          return '等待下一轮'
        case 'pending_human':
          return '待人工处理'
        case 'failed':
          return '失败'
        default:
          return status || '未知'
      }
    }

    const sourceText = (source?: string | null) => {
      switch ((source || '').toLowerCase()) {
        case 'kb':
          return '知识库'
        case 'llm':
          return '大模型'
        case 'rules':
          return '规则引擎'
        case 'search':
          return '外部搜索'
        default:
          return source || '-'
      }
    }

    const eventStatusType = (status?: string) => {
      switch ((status || '').toLowerCase()) {
        case 'error':
        case 'exception':
          return 'danger'
        case 'success':
        case 'ok':
          return 'success'
        case 'warning':
          return 'warning'
        default:
          return 'info'
      }
    }

    const formatStatusText = (status?: string) => {
      if (!status) return '未知'
      switch (status.toLowerCase()) {
        case 'ok':
          return '正常'
        case 'healthy':
          return '健康'
        case 'warning':
          return '警告'
        case 'error':
        case 'unhealthy':
          return '异常'
        default:
          return status
      }
    }

    watch(
      () => resourceFilters.clusterId,
      () => {
        resourceFilters.page = 1
        loadResources()
      }
    )

    watch(
      () => metricsForm.cluster_id,
      () => {
        metricsResult.value = null
      }
    )

    watch(
      () => logForm.cluster_id,
      () => {
        logResult.value = null
      }
    )

    onMounted(async () => {
      await loadClusters()
      if (activeTab.value === 'resources') {
        loadResources()
      }
      if (activeTab.value === 'diagnosis') {
        await loadDiagnosis()
        // 检查是否有进行中的诊断，如果有则启动轮询
        await nextTick()
        const hasRunningDiagnosis = diagnosisList.value.some(
          (record) => ['pending', 'running', 'pending_next'].includes(record.status?.toLowerCase() || '')
        )
        if (hasRunningDiagnosis) {
          startDiagnosisPolling()
        }
      }
      // 设置配置信息表格列宽
      fixConfigDescriptionsWidth()
    })

    onUnmounted(() => {
      // 清理定时器
      stopDiagnosisPolling()
    })

    // 动态设置配置信息表格的列宽为 50/50
    const fixConfigDescriptionsWidth = () => {
      nextTick(() => {
        const configDescriptions = document.querySelectorAll('.config-descriptions .el-descriptions__table')
        configDescriptions.forEach((table: any) => {
          // 设置 table-layout
          if (table) {
            table.style.tableLayout = 'fixed'
            table.style.width = '100%'
            
            // 设置 colgroup
            let colgroup = table.querySelector('colgroup')
            if (!colgroup) {
              colgroup = document.createElement('colgroup')
              table.insertBefore(colgroup, table.firstChild)
            }
            
            // 确保有两个 col 元素
            let cols = colgroup.querySelectorAll('col')
            if (cols.length < 2) {
              colgroup.innerHTML = '<col style="width: 50% !important;"><col style="width: 50% !important;">'
            } else {
              cols.forEach((col: any) => {
                col.style.width = '50%'
                col.style.minWidth = '50%'
                col.style.maxWidth = '50%'
              })
            }
            
            // 强制设置 td 宽度，并防止文本溢出
            const tds = table.querySelectorAll('tbody td')
            tds.forEach((td: any, index: number) => {
              if (index % 2 === 0) {
                // 第一列（标签列）
                td.style.width = '50%'
                td.style.minWidth = '50%'
                td.style.maxWidth = '50%'
                td.style.boxSizing = 'border-box'
                td.style.overflow = 'hidden'
                td.style.wordBreak = 'break-word'
                td.style.overflowWrap = 'break-word'
                // 确保标签列内容不会溢出
                const label = td.querySelector('.el-descriptions__label')
                if (label) {
                  label.style.width = '100%'
                  label.style.maxWidth = '100%'
                  label.style.boxSizing = 'border-box'
                  label.style.overflow = 'hidden'
                  label.style.wordBreak = 'break-word'
                  label.style.overflowWrap = 'break-word'
                  label.style.whiteSpace = 'normal'
                }
              } else {
                // 第二列（内容列）
                td.style.width = '50%'
                td.style.minWidth = '50%'
                td.style.maxWidth = '50%'
                td.style.boxSizing = 'border-box'
                td.style.overflow = 'hidden'
                td.style.wordBreak = 'break-word'
                td.style.overflowWrap = 'break-word'
                // 确保内容列内容不会溢出
                const content = td.querySelector('.el-descriptions__content')
                if (content) {
                  content.style.width = '100%'
                  content.style.maxWidth = '100%'
                  content.style.boxSizing = 'border-box'
                  content.style.overflow = 'hidden'
                  content.style.wordBreak = 'break-word'
                  content.style.overflowWrap = 'break-word'
                  content.style.whiteSpace = 'normal'
                }
              }
            })
          }
        })
      })
    }

    // 在组件更新后设置列宽
    onUpdated(() => {
      fixConfigDescriptionsWidth()
    })

    return {
      Monitor,
      ArrowDown,
      MoreFilled,
      Edit,
      Delete,
      activeTab,
      pageLoading,
      clusters,
      clusterPagination,
      clusterDialog,
      clusterFormRef,
      clusterRules,
      openClusterDialog,
      submitClusterForm,
      handleDeleteCluster,
      handleTestConnectivity,
      handleHealthCheck,
      loadClusters,
      PROM_AUTH_OPTIONS,
      LOG_AUTH_OPTIONS,
      connectivityDialog,
      healthStatusTagType,
      formatStatusText,
      resourceTypeOptions,
      resourceFilters,
      resourceSnapshots,
      resourceLoading,
      resourcePagination,
      loadResources,
      handleResourcePageChange,
      handleManualSync,
      recentSyncEvents,
      eventTagType,
      stringify,
      metricTemplateOptions,
      defaultTimeRange,
      metricsForm,
      metricsResult,
      metricsSeries,
      chartOptions,
      handleTemplateChange,
      handleQueryMetrics,
      resetMetricsForm,
      needsNamespace,
      needsPod,
      needsWindow,
      namespaceLoading,
      podLoading,
      namespaces,
      pods,
      handleNamespaceChange,
      logForm,
      logResult,
      handleQueryLogs,
      resetLogForm,
      renderHighlight,
      logLevelTagType,
      diagnosisPagination,
      diagnosisList,
      diagnosisLoading,
      loadDiagnosis,
      diagnosisStatusTag,
      formatDiagnoseStatus,
      sourceText,
      diagnosisDialog,
      diagnosisNamespaces,
      diagnosisNamespaceLoading,
      diagnosisResources,
      diagnosisResourceLoading,
      openManualDiagnosis,
      handleDiagnosisClusterChange,
      handleDiagnosisNamespaceChange,
      handleDiagnosisResourceTypeChange,
      submitManualDiagnosis,
      diagnosisDrawer,
      diagnosisUpdatedAt,
      diagnosisConfidencePercent,
      diagnosisConfidenceStatus,
      feedbackForm,
      feedbackOptions,
      requiresFeedbackNotes,
      feedbackNotesPlaceholder,
      iterationOptions,
      feedbackState,
      feedbackStateDescription,
      feedbackLatest,
      formatFeedbackType,
      submitFeedback,
      iterationLoading,
      iterationTimeline,
      memoryLoading,
      memoryTimeline,
      diagnosisReport,
      openDiagnosisDetail,
      handleDeleteDiagnosis,
      handleDeleteDiagnosisFromDetail,
      getRootCauseAnalysis,
      getWhySteps,
      getTimeline,
      getImpactScope,
      getStructuredSolutions,
      eventStatusType,
      copyRaw,
      handleTabChange,
      formatDateTime,
      getEvidenceIcon,
      getEvidenceTitle,
      isErrorLog,
      formatConfigValue,
      getEventIcon,
      getEventIconClass,
      getEventAlertType,
      getEventAlertClass,
      formatMetricValue,
      getMetricValueClass,
      getAllEvidenceChain
    }
  }
  }
)
