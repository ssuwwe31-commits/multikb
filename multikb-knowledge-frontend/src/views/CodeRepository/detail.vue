<template>
  <div class="code-repository-detail">
    <!-- 顶部信息卡片 -->
    <el-card class="header-card">
      <div class="repo-header">
        <div class="repo-info">
          <h2>{{ repository?.repo_name }}</h2>
          <div class="meta-info">
            <el-tag>{{ repository?.default_branch }}</el-tag>
            <el-tag type="info">{{ repository?.repo_type }}</el-tag>
            <span class="commit-info" v-if="repository?.last_commit_hash">
              最新提交: {{ repository.last_commit_hash.substring(0, 8) }}
            </span>
          </div>
        </div>
        <div class="actions">
          <el-button :icon="Refresh" @click="refreshAnalysis">刷新分析</el-button>
          <el-button type="primary" :icon="ChatDotRound" @click="showQADialog = true">
            代码问答
          </el-button>
          <el-button :icon="Back" @click="goBack">返回</el-button>
        </div>
      </div>
    </el-card>

    <!-- Tab 切换 -->
    <el-card class="tabs-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- Tab 1: 项目概览 -->
        <el-tab-pane label="项目概览" name="overview">
          <div v-loading="summaryLoading">
            <el-card class="summary-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span>项目摘要</span>
                  <el-button size="small" @click="loadSummary">重新生成</el-button>
                </div>
              </template>
              <div class="summary-content" v-html="formattedSummary"></div>
            </el-card>

            <el-card class="stats-card" shadow="never">
              <template #header>统计信息</template>
              
              <!-- 基础统计 -->
              <div class="stats-section">
                <h4 class="stats-title">基础统计</h4>
                <el-row :gutter="20">
                  <el-col :span="6">
                    <el-statistic title="文件总数" :value="statistics?.total_files || 0" />
                  </el-col>
                  <el-col :span="6">
                    <el-statistic title="代码行数" :value="statistics?.total_lines || 0" />
                  </el-col>
                  <el-col :span="6">
                    <el-statistic title="函数数量" :value="statistics?.total_functions || 0" />
                  </el-col>
                  <el-col :span="6">
                    <el-statistic title="类数量" :value="statistics?.total_classes || 0" />
                  </el-col>
                </el-row>
              </div>

              <el-divider />

              <!-- API 接口统计 -->
              <div class="stats-section">
                <h4 class="stats-title">API 接口统计</h4>
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-statistic 
                      title="前端接口数量" 
                      :value="statistics?.api_endpoints?.frontend || 0" 
                    >
                      <template #suffix>
                        <el-tag size="small" type="success">Frontend</el-tag>
                      </template>
                    </el-statistic>
                  </el-col>
                  <el-col :span="8">
                    <el-statistic 
                      title="后端接口数量" 
                      :value="statistics?.api_endpoints?.backend || 0"
                    >
                      <template #suffix>
                        <el-tag size="small" type="warning">Backend</el-tag>
                      </template>
                    </el-statistic>
                  </el-col>
                  <el-col :span="8">
                    <el-statistic 
                      title="数据库表数量" 
                      :value="statistics?.database_tables || 0"
                    >
                      <template #suffix>
                        <el-tag size="small" type="info">Tables</el-tag>
                      </template>
                    </el-statistic>
                  </el-col>
                </el-row>
              </div>

              <el-divider />

              <!-- 外部依赖服务 -->
              <div class="stats-section" v-if="statistics?.external_services?.length > 0">
                <h4 class="stats-title">外部依赖服务</h4>
                <div class="services-list">
                  <el-tag 
                    v-for="service in statistics.external_services" 
                    :key="service.name"
                    :type="getServiceTagType(service.type)"
                    size="large"
                    class="service-tag"
                  >
                    {{ service.name }}
                    <el-badge :value="service.count" class="service-badge" />
                  </el-tag>
                </div>
                <el-empty 
                  v-if="!statistics?.external_services || statistics.external_services.length === 0"
                  description="未检测到外部依赖服务" 
                  :image-size="80"
                />
              </div>

              <el-divider />

              <!-- 语言分布 -->
              <div class="languages-section">
                <h4>语言分布</h4>
                <div class="languages-chart" ref="languagesChartRef" style="height: 300px"></div>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 代码结构 -->
        <el-tab-pane label="代码结构" name="structure">
          <div v-loading="structureLoading" style="height: calc(100vh - 200px); overflow: hidden;">
            <CodeStructureWiki
              :repository="repository"
              :code-structure="codeStructure"
              :repo-id="repoId"
              @view-file="viewFileDetail"
              @refresh="handleWikiRefresh"
            />
          </div>
        </el-tab-pane>

        <!-- Tab 3: 依赖关系 -->
        <el-tab-pane label="依赖关系" name="dependencies">
          <div v-loading="dependenciesLoading">
            <el-card shadow="never">
              
              <div class="dependencies-chart" ref="dependenciesChartRef" style="height: 600px"></div>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 文件详情对话框 -->
    <el-dialog
      v-model="showFileDialog"
      title="文件详情"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="selectedFile">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件路径">{{ selectedFile.file_path }}</el-descriptions-item>
          <el-descriptions-item label="语言">{{ selectedFile.language }}</el-descriptions-item>
          <el-descriptions-item label="代码行数">{{ selectedFile.lines }}</el-descriptions-item>
          <el-descriptions-item label="复杂度">{{ selectedFile.complexity?.cyclomatic || 0 }}</el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <h4>符号列表</h4>
        <el-table :data="selectedFile.symbols" style="width: 100%">
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.type === 'function' ? 'primary' : 'success'">
                {{ row.type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="200" />
          <el-table-column prop="line" label="行号" width="100" />
          <el-table-column label="文档字符串" min-width="300">
            <template #default="{ row }">
              <span class="docstring">{{ row.docstring || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>

        <el-divider />

        <h4>导入语句</h4>
        <el-table :data="selectedFile.imports" style="width: 100%">
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="module" label="模块" min-width="200" />
          <el-table-column prop="line" label="行号" width="100" />
        </el-table>
      </div>
    </el-dialog>

    <!-- 问答对话框 -->
    <el-dialog
      v-model="showQADialog"
      title="代码问答"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="qa-container">
        <!-- 历史对话 -->
        <div class="qa-history" ref="qaHistoryRef">
          <div
            v-for="(item, index) in qaHistory"
            :key="index"
            class="qa-item"
          >
            <div class="question">
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ item.question }}</span>
            </div>
            <div class="answer">
              <el-icon><Document /></el-icon>
              <div v-html="formatAnswer(item.answer)"></div>
              <div class="sources" v-if="item.sources && item.sources.length">
                <span>相关文件：</span>
                <el-tag
                  v-for="(file, idx) in item.sources"
                  :key="idx"
                  size="small"
                  style="margin-right: 5px"
                >
                  {{ file }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入框 -->
        <div class="qa-input">
          <el-input
            v-model="currentQuestion"
            placeholder="输入你的问题..."
            @keyup.enter="handleAskQuestion"
            :disabled="qaLoading"
          >
            <template #append>
              <el-button
                :icon="ChatDotRound"
                @click="handleAskQuestion"
                :loading="qaLoading"
              >
                提问
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Back, ChatDotRound, Search, Document } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import * as codeRepositoryApi from '@/api/modules/code-repository'
import type { CodeRepository, CodeStructure, DependencyGraph, QAResult, WikiContent } from '@/api/modules/code-repository'
import CodeStructureWiki from '@/components/CodeRepository/CodeStructureWiki.vue'

const route = useRoute()
const router = useRouter()

// 基础数据
const repoId = ref(parseInt(route.params.id as string))
const repository = ref<CodeRepository>()
const activeTab = ref('overview')

// 概览数据
const summaryLoading = ref(false)
const summary = ref('')
const statistics = ref<any>()
const wikiContent = ref<WikiContent | null>(null)

// 代码结构数据
const structureLoading = ref(false)
const codeStructure = ref<CodeStructure>()
const fileSearchKeyword = ref('')
const showFileDialog = ref(false)
const selectedFile = ref<any>()

// 依赖关系数据
const dependenciesLoading = ref(false)
const dependencies = ref<DependencyGraph>()

// 问答数据
const showQADialog = ref(false)
const currentQuestion = ref('')
const qaHistory = ref<QAResult[]>([])
const qaLoading = ref(false)

// ECharts 实例
const languagesChartRef = ref()
const dependenciesChartRef = ref()
let languagesChart: any = null
let dependenciesChart: any = null

// 计算属性
const formattedSummary = computed(() => {
  if (!summary.value) return ''
  // 简单的 Markdown 转 HTML
  return summary.value
    .replace(/\n/g, '<br/>')
    .replace(/## (.*)/g, '<h3>$1</h3>')
    .replace(/### (.*)/g, '<h4>$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
})

const filteredFiles = computed(() => {
  if (!codeStructure.value?.files) return []
  if (!fileSearchKeyword.value) return codeStructure.value.files
  
  const keyword = fileSearchKeyword.value.toLowerCase()
  return codeStructure.value.files.filter(file =>
    file.file_path.toLowerCase().includes(keyword)
  )
})


// 加载仓库信息
const loadRepository = async () => {
  try {
    const res = await codeRepositoryApi.getRepository(repoId.value)
    repository.value = res.data
  } catch (error: any) {
    console.error('加载仓库信息失败:', error)
    ElMessage.error('加载仓库信息失败')
  }
}

// 加载项目摘要（优先从缓存获取）
const loadSummary = async () => {
  summaryLoading.value = true
  try {
    // 1. 获取 Wiki 内容（优先从缓存获取）
    const wikiRes = await codeRepositoryApi.getWikiContent(repoId.value, false)
    if (wikiRes.data) {
      // 检查是否是 WikiContent 类型
      if ('project_overview' in wikiRes.data) {
        wikiContent.value = wikiRes.data as WikiContent
        summary.value = wikiRes.data.project_overview
      } else if ('status' in wikiRes.data && wikiRes.data.status === 'processing') {
        // 任务正在生成中，等待后重试一次
        ElMessage.info('项目概述正在生成中，请稍候...')
        await new Promise(resolve => setTimeout(resolve, 3000))
        const retryRes = await codeRepositoryApi.getWikiContent(repoId.value, false)
        if (retryRes.data && 'project_overview' in retryRes.data) {
          wikiContent.value = retryRes.data as WikiContent
          summary.value = retryRes.data.project_overview
        }
      }
    }
    
    // 2. 获取代码结构（包含统计信息，仅从缓存读取）
    const structureRes = await codeRepositoryApi.getCodeStructure(repoId.value)
    if (structureRes.data && !('status' in structureRes.data)) {
      statistics.value = (structureRes.data as CodeStructure).statistics
    }
    
    // 渲染语言分布图
    nextTick(() => {
      renderLanguagesChart()
      // 调试：检查语言分布数据
      if (statistics.value?.languages) {
        console.log('语言分布数据:', statistics.value.languages)
        const langCount = Object.keys(statistics.value.languages).length
        console.log(`语言种类数: ${langCount}`)
      } else {
        console.warn('语言分布数据不存在')
      }
    })
  } catch (error: any) {
    console.error('加载摘要失败:', error)
    ElMessage.error('加载摘要失败: ' + (error.message || '未知错误'))
  } finally {
    summaryLoading.value = false
  }
}

// 加载代码结构（仅从缓存读取）
const loadStructure = async () => {
  structureLoading.value = true
  try {
    const res = await codeRepositoryApi.getCodeStructure(repoId.value)
    
    if (res.data) {
      // 检查是否有 status 字段（表示未解析）
      if ('status' in res.data && res.data.status === 'not_analyzed') {
        // 代码结构尚未解析，触发异步解析任务
        ElMessage.info('代码结构尚未解析，正在触发解析任务...')
        await triggerStructureAnalysis()
        // 等待3秒后重试
        await new Promise(resolve => setTimeout(resolve, 3000))
        const retryRes = await codeRepositoryApi.getCodeStructure(repoId.value)
        if (retryRes.data && !('status' in retryRes.data)) {
          codeStructure.value = retryRes.data as CodeStructure
        }
      } else {
        // 有缓存数据，直接使用
        codeStructure.value = res.data as CodeStructure
      }
    }
  } catch (error: any) {
    console.error('加载代码结构失败:', error)
    ElMessage.error('加载代码结构失败')
  } finally {
    structureLoading.value = false
  }
}

// 触发代码结构异步解析
const triggerStructureAnalysis = async () => {
  try {
    await codeRepositoryApi.analyzeCodeStructure(repoId.value)
  } catch (error: any) {
    console.error('触发代码结构解析失败:', error)
    ElMessage.error('触发代码结构解析失败')
  }
}

// 加载依赖关系（仅从缓存读取）
const loadDependencies = async () => {
  dependenciesLoading.value = true
  try {
    const res = await codeRepositoryApi.getDependencies(repoId.value)
    
    if (res.data) {
      // 检查是否有 status 字段（表示未解析）
      if ('status' in res.data && res.data.status === 'not_analyzed') {
        // 依赖关系尚未解析，提示用户
        ElMessage.warning('依赖关系尚未解析，请点击刷新按钮触发解析')
        dependencies.value = {
          nodes: [],
          edges: []
        } as DependencyGraph
      } else {
        // 有缓存数据，直接使用
        dependencies.value = res.data as DependencyGraph
      }
    }
    
    // 渲染依赖图
    nextTick(() => {
      renderDependenciesChart()
    })
  } catch (error: any) {
    console.error('加载依赖关系失败:', error)
    ElMessage.error('加载依赖关系失败')
  } finally {
    dependenciesLoading.value = false
  }
}

// 渲染语言分布图
const renderLanguagesChart = () => {
  if (!languagesChartRef.value || !statistics.value?.languages) return
  
  // 检查是否有数据
  const languagesEntries = Object.entries(statistics.value.languages)
  if (languagesEntries.length === 0) {
    console.warn('语言分布数据为空')
    return
  }
  
  if (!languagesChart) {
    languagesChart = echarts.init(languagesChartRef.value)
  }
  
  // 后端返回的格式: {language: {count: X, lines: Y}}
  // 需要提取 count 或 lines 作为 value
  const data = languagesEntries.map(([name, value]) => {
    // value 可能是对象 {count: X, lines: Y} 或直接是数字
    const count = typeof value === 'object' && value !== null ? value.count || value.lines || 0 : value || 0
    return {
      name,
      value: count
    }
  }).filter(item => item.value > 0)  // 过滤掉值为 0 的项
  
  if (data.length === 0) {
    console.warn('语言分布数据全部为 0')
    return
  }
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 文件 ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      textStyle: {
        fontSize: 13
      }
    },
    series: [
      {
        name: '语言分布',
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['60%', '50%'],
        data,
        label: {
          fontSize: 13,
          formatter: '{b}: {d}%'
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }
  
  languagesChart.setOption(option)
}

// 渲染依赖关系图
const renderDependenciesChart = () => {
  if (!dependenciesChartRef.value) return
  
  if (!dependenciesChart) {
    dependenciesChart = echarts.init(dependenciesChartRef.value)
  }
  
  // 渲染文件依赖图
  if (!dependencies.value) return
    
    const nodes = dependencies.value.nodes.map(node => ({
      id: node.id,
      name: node.name,
      symbolSize: Math.max(20, Math.min(60, node.lines / 100)),
      category: node.language,
      label: {
        show: true
      }
    }))
    
    const edges = dependencies.value.edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      label: {
        show: false,
        formatter: edge.type
      }
    }))
    
    const categories = [...new Set(dependencies.value.nodes.map(n => n.language))]
      .map(name => ({ name }))
    
    const option = {
      title: {
        text: '依赖关系图（文件级别）',
        left: 'center',
        textStyle: {
          fontSize: 18,
          fontWeight: '600'
        }
      },
      tooltip: {
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            return `
              <strong>${params.data.name}</strong><br/>
              语言: ${params.data.category}<br/>
              代码行: ${dependencies.value?.nodes.find(n => n.id === params.data.id)?.lines || 0}
            `
          }
          return params.data.label.formatter
        }
      },
      legend: [{
        data: categories.map(c => c.name),
        orient: 'vertical',
        left: 'left',
        textStyle: {
          fontSize: 13
        }
      }],
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: edges,
          categories,
          roam: true,
          zoom: 1.2,
          label: {
            show: true,
            position: 'right',
            formatter: '{b}',
            fontSize: 13,
            fontWeight: '500'
          },
          lineStyle: {
            color: 'source',
            curveness: 0.3
          },
          emphasis: {
            focus: 'adjacency',
            label: {
              fontSize: 14,
              fontWeight: '600'
            },
            lineStyle: {
              width: 2
            }
          },
          force: {
            repulsion: 250,
            edgeLength: 120
          }
        }
      ]
    }
    
    dependenciesChart.setOption(option)
}

// Tab 切换
const handleTabChange = (tabName: string) => {
  if (tabName === 'overview' && !summary.value) {
    loadSummary()
  } else if (tabName === 'structure' && !codeStructure.value) {
    loadStructure()
  } else if (tabName === 'dependencies' && !dependencies.value) {
    loadDependencies()
  }
}

// 获取服务标签类型
const getServiceTagType = (serviceType: string): string => {
  const typeMap: Record<string, string> = {
    '数据库': 'primary',
    '缓存': 'success',
    '消息队列': 'warning',
    '搜索引擎': 'info',
    '注册中心': 'danger',
    '对象存储': '',
    'AI服务': 'success',
    '其他': 'info'
  }
  return typeMap[serviceType] || 'info'
}

// 查看文件详情
const viewFileDetail = (file: any) => {
  selectedFile.value = file
  showFileDialog.value = true
}

// 获取复杂度类型
const getComplexityType = (complexity: number) => {
  if (!complexity) return 'info'
  if (complexity <= 10) return 'success'
  if (complexity <= 20) return 'warning'
  return 'danger'
}

// 刷新分析
const refreshAnalysis = async () => {
  ElMessage.info('重新分析中...')
  // 清空缓存，重新加载
  summary.value = ''
  wikiContent.value = null
  codeStructure.value = undefined
  dependencies.value = undefined
  
  if (activeTab.value === 'overview') {
    await loadSummary()
  } else if (activeTab.value === 'structure') {
    // 刷新时触发异步解析任务
    await triggerStructureAnalysis()
    ElMessage.info('代码结构解析任务已提交，请稍后刷新页面查看结果')
    // 等待3秒后重试加载
    await new Promise(resolve => setTimeout(resolve, 3000))
    await loadStructure()
  } else if (activeTab.value === 'dependencies') {
    await loadDependencies()
  }
}

// Wiki 刷新处理
const handleWikiRefresh = async () => {
  // 触发代码结构异步解析任务
  try {
    ElMessage.info('正在触发代码结构解析任务...')
    await codeRepositoryApi.analyzeCodeStructure(repoId.value)
    ElMessage.success('代码结构解析任务已提交，请稍后刷新页面查看结果')
    
    // 等待3秒后重新加载
    await new Promise(resolve => setTimeout(resolve, 3000))
    await loadStructure()
  } catch (error: any) {
    console.error('触发代码结构解析失败:', error)
    ElMessage.error('触发代码结构解析失败')
  }
}

// 问答功能
const handleAskQuestion = async () => {
  if (!currentQuestion.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  
  const question = currentQuestion.value
  currentQuestion.value = ''
  qaLoading.value = true
  
  try {
    const res = await codeRepositoryApi.codeQA({
      repository_id: repoId.value,
      question
    })
    
    qaHistory.value.push(res.data)
    
    // 滚动到底部
    nextTick(() => {
      const el = document.querySelector('.qa-history')
      if (el) {
        el.scrollTop = el.scrollHeight
      }
    })
  } catch (error: any) {
    console.error('问答失败:', error)
    ElMessage.error('问答失败')
  } finally {
    qaLoading.value = false
  }
}

// 格式化答案
const formatAnswer = (answer: string) => {
  return answer
    .replace(/\n/g, '<br/>')
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

// 返回
const goBack = () => {
  router.back()
}

// 初始化
onMounted(() => {
  loadRepository()
  loadSummary()
})
</script>

<style scoped lang="scss">
.code-repository-detail {
  padding: 20px;
  font-size: 14px;
  
  * {
    line-height: 1.6;
  }

  .header-card {
    margin-bottom: 20px;

    .repo-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .repo-info {
        h2 {
          margin: 0 0 10px 0;
          font-size: 22px;
          font-weight: 600;
          color: #1f2328;
        }

        .meta-info {
          display: flex;
          gap: 10px;
          align-items: center;

          .commit-info {
            color: #57606a;
            font-size: 14px;
          }
        }
      }

      .actions {
        display: flex;
        gap: 10px;
      }
    }
  }

  .tabs-card {
    .summary-card,
    .stats-card {
      margin-bottom: 20px;

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .summary-content {
        font-size: 15px;
        line-height: 1.8;
        color: #303133;
        white-space: pre-wrap;

        :deep(h3) {
          font-size: 18px;
          font-weight: 600;
          margin: 16px 0 10px 0;
          color: #1f2328;
        }

        :deep(h4) {
          font-size: 16px;
          font-weight: 600;
          margin: 14px 0 8px 0;
          color: #1f2328;
        }

        :deep(p) {
          margin: 10px 0;
          line-height: 1.7;
        }

        :deep(ul), :deep(ol) {
          margin: 10px 0;
          padding-left: 24px;
        }

        :deep(li) {
          margin: 6px 0;
          line-height: 1.6;
        }

        :deep(code) {
          background: #f6f8fa;
          color: #d73a49;
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 0.95em;
          font-family: 'Consolas', monospace;
        }

        :deep(strong) {
          font-weight: 600;
        }
      }

      .stats-section {
        margin-bottom: 24px;

        .stats-title {
          margin-bottom: 16px;
          font-size: 16px;
          font-weight: 600;
          color: #1f2328;
          padding-bottom: 8px;
          border-bottom: 2px solid #e8e8e8;
        }

        .services-list {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 12px;

          .service-tag {
            padding: 8px 16px;
            font-size: 14px;
            border-radius: 6px;
            position: relative;
            cursor: pointer;
            transition: all 0.3s;

            &:hover {
              transform: translateY(-2px);
              box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }

            .service-badge {
              margin-left: 8px;
              
              :deep(.el-badge__content) {
                background-color: rgba(0, 0, 0, 0.2);
                border: none;
                font-size: 11px;
                height: 18px;
                line-height: 18px;
                padding: 0 6px;
              }
            }
          }
        }
      }

      .languages-section {
        margin-top: 20px;

        h4 {
          margin-bottom: 15px;
          font-size: 16px;
          font-weight: 600;
          color: #1f2328;
        }
      }
    }

    .docstring {
      font-size: 12px;
      color: #666;
    }
  }

  .qa-container {
    display: flex;
    flex-direction: column;
    height: 500px;

    .qa-history {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      background: #f5f5f5;
      border-radius: 8px;
      margin-bottom: 20px;

      .qa-item {
        margin-bottom: 20px;

        .question {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          margin-bottom: 10px;
          padding: 12px;
          background: #e3f2fd;
          border-radius: 8px;
          font-weight: 500;
        }

        .answer {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 12px;
          background: white;
          border-radius: 8px;
          line-height: 1.8;

          > div {
            flex: 1;
          }

          :deep(code) {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
          }

          :deep(pre) {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 10px 0;

            code {
              background: transparent;
              padding: 0;
            }
          }

          .sources {
            margin-top: 10px;
            font-size: 12px;
            color: #666;

            span {
              margin-right: 10px;
            }
          }
        }
      }
    }

    .qa-input {
      :deep(.el-input-group__append) {
        background: var(--el-color-primary);
        color: white;
        border: none;

        .el-button {
          color: white;
        }
      }
    }
  }
}
</style>
