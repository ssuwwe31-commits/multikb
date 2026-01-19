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
          <el-descriptions-item label="代码行数">
            {{ getFileLines(selectedFile) }}
          </el-descriptions-item>
          <el-descriptions-item label="复杂度">
            {{ getFileComplexity(selectedFile) }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <!-- 文件内容 -->
        <div class="file-content-section">
          <div class="file-content-header">
            <h4>文件内容</h4>
            <el-button 
              size="small" 
              @click="loadFileContent"
              :loading="fileContentLoading"
              v-if="!showFileContent"
            >
              查看内容
            </el-button>
            <el-button 
              size="small" 
              @click="showFileContent = false"
              v-else
            >
              隐藏内容
            </el-button>
          </div>
          
          <div v-if="showFileContent" class="file-content-wrapper">
            <div v-loading="fileContentLoading" class="file-content">
              <div v-if="fileContent" class="code-viewer">
                <div class="code-toolbar">
                  <div class="toolbar-left">
                    <el-button-group>
                      <el-button 
                        size="small" 
                        @click="handleGoToDefinition" 
                        :disabled="currentLine === 0"
                        :title="currentLine > 0 ? '跳转到当前选中符号的定义位置' : '请先点击代码中的符号'"
                      >
                        <el-icon><Position /></el-icon>
                        跳转到定义
                      </el-button>
                      <el-button 
                        size="small" 
                        @click="handleFindReferences" 
                        :disabled="currentLine === 0"
                        :title="currentLine > 0 ? '查找当前选中符号的所有引用位置' : '请先点击代码中的符号'"
                      >
                        <el-icon><Search /></el-icon>
                        查找引用
                      </el-button>
                      <el-button 
                        size="small" 
                        @click="handleShowHoverInfo" 
                        :disabled="currentLine === 0"
                        :title="currentLine > 0 ? '查看当前选中符号的详细信息' : '请先点击代码中的符号'"
                      >
                        <el-icon><InfoFilled /></el-icon>
                        查看信息
                      </el-button>
                    </el-button-group>
                    <el-button 
                      size="small" 
                      type="primary"
                      @click="handleExplainCode" 
                      :disabled="!selectedCode"
                      :title="selectedCode ? '解释选中的代码' : '请先选中一段代码'"
                      style="margin-left: 12px;"
                    >
                      <el-icon><Document /></el-icon>
                      解释代码
                    </el-button>
                    <el-text v-if="currentLine === 0 && !selectedCode" type="info" size="small" style="margin-left: 12px;">
                      💡 提示：点击代码中的符号（函数名、类名等）后，即可使用导航功能；或选中代码后使用"解释代码"功能
                    </el-text>
                    <el-text v-else-if="currentLine > 0" type="success" size="small" style="margin-left: 12px;">
                      ✅ 已选择位置: 行 {{ currentLine }}, 列 {{ currentColumn }}，可以使用导航功能
                    </el-text>
                    <el-text v-else-if="selectedCode" type="success" size="small" style="margin-left: 12px;">
                      ✅ 已选中代码（{{ selectedCode.length }} 字符），可以点击"解释代码"
                    </el-text>
                  </div>
                  <span class="code-position" v-if="currentLine > 0">
                    行 {{ currentLine }}, 列 {{ currentColumn }}
                  </span>
                </div>
                <div ref="codeElement" class="code-container">
                  <pre 
                    @click="handleCodeClick"
                    @mousemove="handleCodeHover"
                    @mouseup="handleCodeSelection"
                    class="code-content"
                  >
                    <code>{{ fileContent }}</code>
                  </pre>
                </div>
              </div>
              <el-empty v-else description="无法加载文件内容" />
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 代码解释对话框 -->
    <el-dialog
      v-model="showExplanationDialog"
      title="📝 代码解释"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-loading="explanationLoading">
        <div v-if="codeExplanation" class="explanation-content">
          <div class="explanation-header">
            <el-tag v-if="codeExplanation.language" type="info" style="margin-right: 8px;">
              {{ codeExplanation.language }}
            </el-tag>
            <el-text v-if="codeExplanation.file_path" type="info" size="small">
              文件: {{ codeExplanation.file_path }}
            </el-text>
          </div>
          <el-divider />
          <div class="code-section">
            <h4>选中的代码：</h4>
            <pre class="code-block"><code>{{ codeExplanation.code }}</code></pre>
          </div>
          <el-divider />
          <div class="explanation-section">
            <h4>解释：</h4>
            <div class="explanation-text" v-html="formatExplanation(codeExplanation.explanation)"></div>
          </div>
        </div>
        <el-empty v-else description="暂无解释内容" />
      </div>
      <template #footer>
        <el-button @click="showExplanationDialog = false">关闭</el-button>
        <el-button type="primary" @click="handleExplainCode" :loading="explanationLoading">
          重新解释
        </el-button>
      </template>
    </el-dialog>

    <!-- 引用列表对话框 -->
    <el-dialog
      v-model="showReferencesDialog"
      title="引用位置"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="referencesList.length > 0">
        <el-table :data="referencesList" stripe style="width: 100%">
          <el-table-column prop="file_path" label="文件路径" min-width="300" />
          <el-table-column prop="line" label="行号" width="100" />
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag :type="getReferenceTypeTag(row.type)">
                {{ getReferenceTypeLabel(row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="context" label="上下文" min-width="400">
            <template #default="{ row }">
              <pre class="context-preview">{{ row.context || '无' }}</pre>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button
                size="small"
                type="primary"
                @click="navigateToReference(row)"
              >
                跳转
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-else description="未找到引用位置" />
    </el-dialog>

    <!-- 问答对话框 -->
    <el-dialog
      v-model="showQADialog"
      title="💬 代码智能问答"
      width="85%"
      :close-on-click-modal="false"
      class="qa-dialog"
    >
      <template #header>
        <div class="dialog-header">
          <div class="header-left">
            <el-icon class="header-icon"><ChatDotRound /></el-icon>
            <span class="header-title">代码智能问答</span>
            <el-tag size="small" type="success" effect="plain">AI 助手</el-tag>
          </div>
          <div class="header-actions">
            <el-button 
              text 
              size="small" 
              @click="qaHistory = []"
              :disabled="qaHistory.length === 0"
            >
              <el-icon><Delete /></el-icon>
              清空对话
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="qa-container">
        <!-- 历史对话 -->
        <div class="qa-history" ref="qaHistoryRef">
          <!-- 空状态 -->
          <div v-if="qaHistory.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="64"><ChatDotRound /></el-icon>
            </div>
            <h3 class="empty-title">开始你的代码问答之旅</h3>
            <p class="empty-description">你可以询问关于代码库的任何问题，比如：</p>
            <div class="example-questions">
              <el-tag 
                v-for="(example, idx) in exampleQuestions" 
                :key="idx"
                class="example-tag"
                @click="currentQuestion = example"
                effect="plain"
              >
                {{ example }}
              </el-tag>
            </div>
          </div>
          
          <!-- 对话列表 -->
          <div
            v-for="(item, index) in qaHistory"
            :key="index"
            class="qa-item"
          >
            <!-- 问题 -->
            <div class="message-bubble question-bubble">
              <div class="bubble-avatar user-avatar">
                <el-icon><User /></el-icon>
              </div>
              <div class="bubble-content">
                <div class="bubble-header">
                  <span class="bubble-name">你</span>
                  <span class="bubble-time">{{ formatTime(item.created_at) }}</span>
                </div>
                <div class="bubble-text">{{ item.question }}</div>
              </div>
            </div>
            
            <!-- 答案 -->
            <div class="message-bubble answer-bubble">
              <div class="bubble-avatar ai-avatar">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <div class="bubble-content">
                <div class="bubble-header">
                  <span class="bubble-name">AI 助手</span>
                  <span class="bubble-time">{{ formatTime(item.created_at) }}</span>
                </div>
                <div 
                  class="bubble-text answer-content markdown-body"
                  v-html="formatAnswer(item.answer)"
                  :data-qa-index="index"
                ></div>
                <div class="sources" v-if="item.sources && item.sources.length">
                  <el-divider content-position="left" style="margin: 12px 0;">
                    <span style="font-size: 12px; color: #909399;">参考来源</span>
                  </el-divider>
                  <div class="sources-list">
                    <el-tag
                      v-for="(file, idx) in item.sources"
                      :key="idx"
                      size="small"
                      type="info"
                      effect="plain"
                      class="source-tag clickable"
                      @click="handleSourceFileClick(file)"
                    >
                      <el-icon><Document /></el-icon>
                      {{ file }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 加载状态 -->
          <div v-if="qaLoading" class="loading-bubble">
            <div class="bubble-avatar ai-avatar">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="bubble-content">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入框 -->
        <div class="qa-input-area">
          <div class="input-wrapper">
            <el-input
              v-model="currentQuestion"
              type="textarea"
              :rows="3"
              placeholder="输入你的问题，按 Ctrl+Enter 发送..."
              @keydown.ctrl.enter="handleAskQuestion"
              @keydown.meta.enter="handleAskQuestion"
              :disabled="qaLoading"
              class="question-input"
              resize="none"
            />
            <div class="input-actions">
              <div class="input-tips">
                <el-text size="small" type="info">
                  <el-icon><InfoFilled /></el-icon>
                  支持 Markdown 和流程图
                </el-text>
              </div>
              <el-button
                type="primary"
                :icon="ChatDotRound"
                @click="handleAskQuestion"
                :loading="qaLoading"
                :disabled="!currentQuestion.trim()"
                class="send-button"
                size="large"
              >
                {{ qaLoading ? '思考中...' : '发送' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Back, ChatDotRound, Search, Document, Delete, User, InfoFilled, Position } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import * as codeRepositoryApi from '@/api/modules/code-repository'
import type { CodeRepository, CodeStructure, DependencyGraph, QAResult, WikiContent, NavigationLocation, HoverInfo, CodeExplanationResponse } from '@/api/modules/code-repository'
import CodeStructureWiki from '@/components/CodeRepository/CodeStructureWiki.vue'
import { marked } from 'marked'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

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
const fileContent = ref('')
const fileContentLoading = ref(false)
const showFileContent = ref(false)
const codeElement = ref<HTMLElement>()
const currentLine = ref(0)
const currentColumn = ref(0)
const canNavigate = ref(false)
const showReferencesDialog = ref(false)
const referencesList = ref<NavigationLocation[]>([])
const targetLine = ref(0) // 用于滚动到指定行

// 代码解释相关
const selectedCode = ref('') // 选中的代码
const showExplanationDialog = ref(false)
const explanationLoading = ref(false)
const codeExplanation = ref<CodeExplanationResponse | null>(null)

// 依赖关系数据
const dependenciesLoading = ref(false)
const dependencies = ref<DependencyGraph>()

// 问答数据
const showQADialog = ref(false)
const currentQuestion = ref('')
const qaHistory = ref<QAResult[]>([])
const qaLoading = ref(false)
const qaHistoryRef = ref<HTMLElement>()
const currentSessionId = ref<string | null>(null) // 当前会话ID

// 示例问题
const exampleQuestions = [
  '这个项目的架构是什么样的？',
  '如何启动这个项目？',
  '主要的依赖有哪些？',
  '核心功能是如何实现的？',
  '数据库设计是怎样的？'
]

// 格式化时间
const formatTime = (dateStr?: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / (1000 * 60))
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// 监听问答历史变化，重新渲染 Mermaid
watch(() => qaHistory.value.length, async () => {
  if (qaHistory.value.length > 0) {
    await nextTick()
    setTimeout(() => {
      renderAllMermaidDiagrams()
    }, 200)
  }
})

// 监听 canNavigate 状态变化（用于调试）
watch(() => canNavigate.value, (newVal) => {
  console.log('canNavigate 状态变化:', newVal, 'currentLine:', currentLine.value)
})

// 监听 currentLine 状态变化（用于调试）
watch(() => currentLine.value, (newVal) => {
  console.log('currentLine 状态变化:', newVal)
  if (newVal > 0 && !canNavigate.value) {
    console.log('检测到 currentLine > 0 但 canNavigate 为 false，自动启用')
    canNavigate.value = true
  }
})

// 监听对话框显示，渲染 Mermaid
watch(showQADialog, async (visible) => {
  if (visible && qaHistory.value.length > 0) {
    await nextTick()
    setTimeout(() => {
      renderAllMermaidDiagrams()
    }, 300)
  }
})

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
        // 任务正在生成中，不立即重试，避免重复发送任务
        ElMessage.info('项目概述正在生成中，请稍候...')
        // 不再自动重试，让用户手动刷新或等待任务完成
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

// 获取文件行数
const getFileLines = (file: any): string => {
  if (!file) return '-'
  // 尝试多种可能的字段名
  if (file.lines !== undefined && file.lines !== null) {
    return file.lines.toString()
  }
  if (file.lines_count !== undefined && file.lines_count !== null) {
    return file.lines_count.toString()
  }
  // 如果有文件内容，计算行数
  if (fileContent.value) {
    return fileContent.value.split('\n').length.toString()
  }
  return '-'
}

// 获取文件复杂度
const getFileComplexity = (file: any): string => {
  if (!file) return '-'
  // 尝试多种可能的字段名和结构
  if (file.complexity) {
    if (typeof file.complexity === 'number') {
      return file.complexity.toString()
    }
    if (file.complexity.cyclomatic !== undefined) {
      return file.complexity.cyclomatic.toString()
    }
    if (file.complexity.total !== undefined) {
      return file.complexity.total.toString()
    }
  }
  if (file.complexity_score !== undefined && file.complexity_score !== null) {
    return file.complexity_score.toString()
  }
  return '-'
}

// 查看文件详情
const viewFileDetail = (file: any) => {
  selectedFile.value = file
  showFileDialog.value = true
  showFileContent.value = false
  fileContent.value = ''
}

// 加载文件内容
const loadFileContent = async () => {
  if (!selectedFile.value || !selectedFile.value.file_path) {
    ElMessage.warning('文件信息不完整')
    return
  }
  
  fileContentLoading.value = true
  try {
    const res = await codeRepositoryApi.getFileContent(
      selectedFile.value.file_path,
      repoId.value
    )
    if (res.data && res.data.content) {
      fileContent.value = res.data.content
      showFileContent.value = true
      
      // 如果文件没有行数信息，从内容计算
      if (!selectedFile.value.lines && !selectedFile.value.lines_count) {
        const lineCount = fileContent.value.split('\n').length
        // 更新 selectedFile 的行数（仅用于显示）
        if (!selectedFile.value.lines) {
          selectedFile.value.lines = lineCount
        }
      }
      
      // 重置导航状态
      currentLine.value = 0
      currentColumn.value = 0
      canNavigate.value = false
    } else {
      ElMessage.warning('文件内容为空')
    }
  } catch (error: any) {
    console.error('加载文件内容失败:', error)
    ElMessage.error(error.message || '加载文件内容失败')
  } finally {
    fileContentLoading.value = false
  }
}

// 处理代码点击（获取行号和列号）
const handleCodeClick = (event: MouseEvent) => {
  console.log('代码点击事件触发', event)
  
  // 阻止事件冒泡，避免触发其他点击事件
  event.stopPropagation()
  
  // 直接使用 event.currentTarget（pre 元素）
  const pre = event.currentTarget as HTMLElement
  
  if (!pre || pre.tagName !== 'PRE') {
    console.warn('未找到 pre 元素')
    return
  }
  
  const text = fileContent.value
  if (!text) {
    console.warn('文件内容为空')
    ElMessage.warning('文件内容为空，无法选择位置')
    return
  }
  
  const lines = text.split('\n')
  
  // 计算点击位置对应的行号和列号
  const rect = pre.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  
  // 获取实际的行高和字符宽度
  const computedStyle = window.getComputedStyle(pre)
  const lineHeight = parseFloat(computedStyle.lineHeight) || 20
  const fontSize = parseFloat(computedStyle.fontSize) || 14
  const charWidth = fontSize * 0.6 // 估算字符宽度（等宽字体约为字体大小的 0.6 倍）
  
  // 考虑滚动位置
  const scrollTop = pre.scrollTop || 0
  const relativeY = y + scrollTop
  
  // 计算行号（从1开始）
  const line = Math.max(1, Math.floor(relativeY / lineHeight) + 1)
  
  // 计算列号（从0开始）
  // 获取当前行的文本
  const currentLineText = lines[line - 1] || ''
  // 计算点击位置对应的列号
  const paddingLeft = parseFloat(computedStyle.paddingLeft) || 0
  const relativeX = x - paddingLeft
  const column = Math.max(0, Math.floor(relativeX / charWidth))
  
  // 确保行号和列号在有效范围内
  const validLine = Math.min(line, lines.length)
  const validColumn = Math.min(column, currentLineText.length)
  
  console.log('计算的位置信息:', {
    x, y, relativeY, relativeX,
    lineHeight, fontSize, charWidth,
    validLine, validColumn,
    currentLineText: currentLineText.substring(0, 50),
    scrollTop
  })
  
  // 更新状态（直接设置，Vue 会自动响应）
  currentLine.value = validLine
  currentColumn.value = validColumn
  canNavigate.value = true
  
  console.log('状态已更新:', {
    canNavigate: canNavigate.value,
    currentLine: currentLine.value,
    currentColumn: currentColumn.value
  })
  
  // 高亮当前行（可选）
  highlightCurrentLine(validLine)
  
  // 使用 nextTick 确保 DOM 更新后再显示消息
  nextTick(() => {
    ElMessage.success({
      message: `已选择位置: 行 ${validLine}, 列 ${validColumn}，现在可以使用导航功能了`,
      duration: 2000
    })
  })
}

// 高亮当前行
const highlightCurrentLine = (line: number) => {
  if (!codeElement.value) return
  
  // 移除之前的高亮
  const pre = codeElement.value.querySelector('pre')
  if (!pre) return
  
  // 简单的行高亮：可以通过添加背景色实现
  // 这里只是标记，实际高亮可以通过 CSS 实现
}

// 处理代码悬停
const handleCodeHover = (event: MouseEvent) => {
  // 可以在这里实现悬停显示信息的功能
}

// 处理代码选择
const handleCodeSelection = (event: MouseEvent) => {
  // 等待一小段时间，确保选择完成
  setTimeout(() => {
    const selection = window.getSelection()
    if (!selection || selection.rangeCount === 0) {
      selectedCode.value = ''
      return
    }
    
    const range = selection.getRangeAt(0)
    const selectedText = range.toString().trim()
    
    // 检查选择是否在代码区域内
    const codeContainer = codeElement.value?.querySelector('pre')
    if (!codeContainer) {
      selectedCode.value = ''
      return
    }
    
    // 检查选择是否在代码元素内
    if (codeContainer.contains(range.commonAncestorContainer) || 
        codeContainer === range.commonAncestorContainer) {
      if (selectedText && selectedText.length > 0) {
        selectedCode.value = selectedText
        console.log('选中代码:', selectedText.substring(0, 100))
      } else {
        selectedCode.value = ''
      }
    } else {
      selectedCode.value = ''
    }
  }, 50)
}

// 解释代码
const handleExplainCode = async () => {
  if (!selectedCode.value || selectedCode.value.trim().length === 0) {
    ElMessage.warning('请先选中一段代码')
    return
  }
  
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  explanationLoading.value = true
  showExplanationDialog.value = true
  
  try {
    // 检测编程语言（从文件路径或文件扩展名）
    let language: string | undefined = undefined
    if (selectedFile.value.file_path) {
      const ext = selectedFile.value.file_path.split('.').pop()?.toLowerCase()
      const languageMap: Record<string, string> = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
        'go': 'go',
        'rs': 'rust',
        'php': 'php',
        'rb': 'ruby',
        'swift': 'swift',
        'kt': 'kotlin',
        'scala': 'scala',
        'vue': 'vue',
        'tsx': 'tsx',
        'jsx': 'jsx',
        'html': 'html',
        'css': 'css',
        'scss': 'scss',
        'sql': 'sql',
        'sh': 'bash',
        'bash': 'bash',
        'yaml': 'yaml',
        'yml': 'yaml',
        'json': 'json',
        'xml': 'xml',
        'md': 'markdown'
      }
      language = languageMap[ext || ''] || ext
    }
    
    const res = await codeRepositoryApi.explainCode(repoId.value, {
      code: selectedCode.value,
      file_path: selectedFile.value.file_path,
      language: language
    })
    
    if (res.data) {
      codeExplanation.value = res.data
      ElMessage.success('代码解释生成成功')
    } else {
      ElMessage.error('获取代码解释失败')
    }
  } catch (error: any) {
    console.error('解释代码失败:', error)
    ElMessage.error(error.message || '解释代码失败')
    codeExplanation.value = null
  } finally {
    explanationLoading.value = false
  }
}

// 格式化解释文本（Markdown 转 HTML）
const formatExplanation = (text: string) => {
  if (!text) return ''
  
  // 简单的 Markdown 转 HTML
  return text
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
    .replace(/### (.*?)(<br\/>|$)/g, '<h4>$1</h4>')
    .replace(/## (.*?)(<br\/>|$)/g, '<h3>$1</h3>')
    .replace(/# (.*?)(<br\/>|$)/g, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background: #f5f7fa; padding: 2px 6px; border-radius: 3px; font-family: monospace;">$1</code>')
    .replace(/```([^`]+)```/g, '<pre style="background: #f5f7fa; padding: 10px; border-radius: 4px; overflow-x: auto;"><code>$1</code></pre>')
    .replace(/^(.+)$/, '<p>$1</p>')
}

// 跳转到定义
const handleGoToDefinition = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  if (currentLine.value === 0) {
    ElMessage.info('请先点击代码中的符号（函数名、类名等），然后再点击此按钮')
    return
  }
  
  try {
    const res = await codeRepositoryApi.getDefinition({
      repository_id: repoId.value,
      file_path: selectedFile.value.file_path,
      line: currentLine.value,
      column: currentColumn.value
    })
    
    if (res.data) {
      const definition = res.data
      
      // 检查是否是定义位置本身
      if (definition.is_definition) {
        ElMessage.info(definition.message || '当前位置就是定义位置，无需跳转')
        return
      }
      
      // 如果定义在其他文件，导航到该文件
      if (definition.file_path !== selectedFile.value.file_path) {
        // 跨文件导航
        await navigateToFile(definition.file_path, definition.line)
        ElMessage.success(`已跳转到定义: ${definition.file_path}:${definition.line}`)
      } else {
        // 同一文件，检查是否是同一行
        if (definition.line === currentLine.value) {
          ElMessage.info('当前位置就是定义位置')
          return
        }
        // 滚动到定义位置
        targetLine.value = definition.line
        await scrollToLine(definition.line)
        ElMessage.success(`已跳转到定义: 第 ${definition.line} 行`)
      }
    } else {
      ElMessage.warning('未找到符号定义')
    }
  } catch (error: any) {
    console.error('获取定义失败:', error)
    ElMessage.error(error.message || '获取定义失败')
  }
}

// 查找所有引用
const handleFindReferences = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  if (currentLine.value === 0) {
    ElMessage.info('请先点击代码中的符号（函数名、类名等），然后再点击此按钮')
    return
  }
  
  try {
    const res = await codeRepositoryApi.getReferences({
      repository_id: repoId.value,
      file_path: selectedFile.value.file_path,
      line: currentLine.value,
      column: currentColumn.value,
      include_definition: true
    })
    
    if (res.data && res.data.references && res.data.references.length > 0) {
      referencesList.value = res.data.references
      showReferencesDialog.value = true
      ElMessage.success(`找到 ${res.data.references.length} 个引用位置`)
    } else {
      ElMessage.warning('未找到引用位置')
    }
  } catch (error: any) {
    console.error('获取引用失败:', error)
    ElMessage.error(error.message || '获取引用失败')
  }
}

// 显示悬停信息
const handleShowHoverInfo = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  if (currentLine.value === 0) {
    ElMessage.info('请先点击代码中的符号（函数名、类名等），然后再点击此按钮')
    return
  }
  
  try {
    const res = await codeRepositoryApi.getHoverInfo({
      repository_id: repoId.value,
      file_path: selectedFile.value.file_path,
      line: currentLine.value,
      column: currentColumn.value
    })
    
    if (res.data) {
      const info = res.data
      // 显示悬停信息对话框
      ElMessageBox.alert(
        `<div style="line-height: 1.8;">
          <p><strong>符号:</strong> ${info.symbol_name}</p>
          <p><strong>完整名称:</strong> ${info.qualified_name}</p>
          <p><strong>类型:</strong> ${info.symbol_type}</p>
          <p><strong>签名:</strong> <code style="background: #f5f7fa; padding: 2px 6px; border-radius: 3px;">${info.signature || '无'}</code></p>
          ${info.docstring ? `<p><strong>说明:</strong><br/><pre style="background: #f5f7fa; padding: 10px; border-radius: 4px; white-space: pre-wrap;">${info.docstring}</pre></p>` : ''}
          ${info.file_path ? `<p><strong>位置:</strong> ${info.file_path}:${info.line || '?'}</p>` : ''}
        </div>`,
        '符号信息',
        {
          dangerouslyUseHTMLString: true,
          confirmButtonText: '确定',
          customStyle: {
            width: '600px'
          }
        }
      )
    } else {
      ElMessage.warning('未找到符号信息')
    }
  } catch (error: any) {
    console.error('获取悬停信息失败:', error)
    ElMessage.error(error.message || '获取悬停信息失败')
  }
}

// 导航到引用位置
const navigateToReference = async (ref: NavigationLocation) => {
  showReferencesDialog.value = false
  
  // 如果引用在其他文件，导航到该文件
  if (ref.file_path !== selectedFile.value?.file_path) {
    await navigateToFile(ref.file_path, ref.line)
  } else {
    // 同一文件，滚动到引用位置
    targetLine.value = ref.line
    await scrollToLine(ref.line)
  }
  
  ElMessage.success(`已跳转到: ${ref.file_path}:${ref.line}`)
}

// 导航到文件（跨文件导航）
const navigateToFile = async (filePath: string, line?: number) => {
  try {
    console.log('开始导航到文件:', filePath, '行号:', line)
    
    // 确保代码结构已加载
    if (!codeStructure.value?.files || codeStructure.value.files.length === 0) {
      console.log('代码结构未加载，开始加载...')
      await loadStructure()
      // 等待结构加载完成
      await nextTick()
    }
    
    console.log('代码结构文件数量:', codeStructure.value?.files?.length || 0)
    console.log('查找文件路径:', filePath)
    
    const file = findFileByPath(filePath)
    console.log('找到的文件:', file)
    
    if (file) {
      console.log('打开文件对话框:', file.file_path)
      // 打开文件对话框
      viewFileDetail(file)
      await nextTick()
      
      // 加载文件内容
      console.log('加载文件内容...')
      await loadFileContent()
      
      // 等待文件内容加载完成
      await nextTick()
      // 额外等待，确保 DOM 已更新
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 如果有行号，滚动到指定行
      if (line) {
        console.log('滚动到行:', line)
        targetLine.value = line
        await scrollToLine(line)
      }
      
      console.log('文件导航完成')
    } else {
      console.error('未找到文件，可用文件列表:', codeStructure.value?.files?.map((f: any) => f.file_path).slice(0, 10))
      ElMessage.warning(`未找到文件: ${filePath}`)
    }
  } catch (error: any) {
    console.error('导航到文件失败:', error)
    ElMessage.error(`导航到文件失败: ${error.message || '未知错误'}`)
  }
}

// 滚动到指定行
const scrollToLine = async (line: number) => {
  console.log('开始滚动到行:', line)
  
  // 多次尝试，确保 DOM 已准备好
  let attempts = 0
  const maxAttempts = 10
  
  while (attempts < maxAttempts) {
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))
    
    if (!codeElement.value) {
      console.log(`尝试 ${attempts + 1}/${maxAttempts}: codeElement 未准备好`)
      attempts++
      continue
    }
    
    const pre = codeElement.value.querySelector('pre')
    if (!pre) {
      console.log(`尝试 ${attempts + 1}/${maxAttempts}: pre 元素未找到`)
      attempts++
      continue
    }
    
    // 获取实际的行高
    const computedStyle = window.getComputedStyle(pre)
    const lineHeight = parseFloat(computedStyle.lineHeight) || 20
    const fontSize = parseFloat(computedStyle.fontSize) || 14
    const actualLineHeight = lineHeight || fontSize * 1.5
    
    console.log('行高:', actualLineHeight, '字体大小:', fontSize)
    
    // 计算目标行的位置
    const targetPosition = (line - 1) * actualLineHeight
    
    // 滚动到目标位置
    const container = codeElement.value.closest('.file-content-wrapper') as HTMLElement
    if (container) {
      console.log('滚动容器找到，当前 scrollTop:', container.scrollTop, '目标位置:', targetPosition)
      container.scrollTop = targetPosition - 50 // 留出一些顶部空间
      console.log('滚动完成，新 scrollTop:', container.scrollTop)
      
      // 高亮目标行（可选）
      highlightLine(line)
      return
    } else {
      console.log(`尝试 ${attempts + 1}/${maxAttempts}: 容器未找到`)
    }
    
    attempts++
  }
  
  console.warn('滚动失败：DOM 元素未准备好')
}

// 高亮指定行
const highlightLine = (line: number) => {
  if (!codeElement.value) return
  
  // 移除之前的高亮
  const pre = codeElement.value.querySelector('pre')
  if (!pre) return
  
  // 简单的行高亮实现：通过添加标记
  // 注意：这里只是简单实现，实际可以使用更复杂的代码编辑器
  const lines = fileContent.value.split('\n')
  if (line > 0 && line <= lines.length) {
    // 可以在这里添加高亮逻辑
    // 例如：在行号旁边添加标记，或者使用代码编辑器的高亮功能
  }
}

// 获取引用类型标签
const getReferenceTypeTag = (type: string) => {
  const typeMap: Record<string, string> = {
    'definition': 'success',
    'call': 'primary',
    'reference': 'info'
  }
  return typeMap[type] || 'info'
}

// 获取引用类型标签文本
const getReferenceTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    'definition': '定义',
    'call': '调用',
    'reference': '引用'
  }
  return labelMap[type] || type
}

// 清空问答历史
const handleClearQAHistory = () => {
  qaHistory.value = []
  currentSessionId.value = null
  
  // 清除 localStorage
  const storageKey = `qa_session_${repoId.value}`
  localStorage.removeItem(storageKey)
  
  // 清除所有相关的历史记录备份
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith(`qa_history_${repoId.value}_`)) {
      localStorage.removeItem(key)
    }
  })
  
  ElMessage.success('已清空问答历史')
}

// 处理参考来源文件点击
const handleSourceFileClick = async (filePath: string) => {
  console.log('点击参考来源文件:', filePath)
  
  try {
    // 确保在代码结构标签页
    if (activeTab.value !== 'structure') {
      activeTab.value = 'structure'
      // 等待标签页切换
      await nextTick()
    }
    
    // 导航到文件
    await navigateToFile(filePath)
  } catch (error: any) {
    console.error('打开参考来源文件失败:', error)
    ElMessage.error(`打开文件失败: ${error.message || '未知错误'}`)
  }
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

// 加载问答历史记录
const loadQAHistory = async () => {
  try {
    // 1. 尝试从 localStorage 恢复会话ID
    const storageKey = `qa_session_${repoId.value}`
    const savedSessionId = localStorage.getItem(storageKey)
    
    if (savedSessionId) {
      currentSessionId.value = savedSessionId
      
      try {
        // 2. 从后端加载历史记录
        const res = await codeRepositoryApi.getQARecords(savedSessionId, {
          page: 1,
          page_size: 100 // 加载最近100条记录
        })
        
        if (res.data && res.data.records && res.data.records.length > 0) {
          // 转换格式以匹配前端显示
          qaHistory.value = res.data.records.map((record: any) => ({
            question: record.question,
            answer: record.answer,
            sources: record.sources || [],
            created_at: record.created_at
          }))
          
          console.log('已从后端加载历史问答记录:', qaHistory.value.length, '条')
          
          // 等待 DOM 更新后渲染 Mermaid
          await nextTick()
          setTimeout(() => {
            renderAllMermaidDiagrams()
          }, 200)
          return
        }
      } catch (backendError) {
        console.warn('从后端加载历史记录失败，尝试从 localStorage 恢复:', backendError)
      }
      
      // 3. 如果后端加载失败，尝试从 localStorage 恢复（作为备份）
      const historyKey = `qa_history_${repoId.value}_${savedSessionId}`
      const savedHistory = localStorage.getItem(historyKey)
      if (savedHistory) {
        try {
          qaHistory.value = JSON.parse(savedHistory)
          console.log('已从 localStorage 恢复历史问答记录:', qaHistory.value.length, '条')
          
          // 等待 DOM 更新后渲染 Mermaid
          await nextTick()
          setTimeout(() => {
            renderAllMermaidDiagrams()
          }, 200)
        } catch (parseError) {
          console.warn('解析 localStorage 历史记录失败:', parseError)
        }
      }
    }
  } catch (error: any) {
    console.warn('加载问答历史失败:', error)
    // 失败不影响使用，继续使用空历史
  }
}

// 创建或获取会话ID
const getOrCreateSessionId = async (): Promise<string> => {
  if (currentSessionId.value) {
    return currentSessionId.value
  }
  
  try {
    // 尝试从 localStorage 恢复
    const storageKey = `qa_session_${repoId.value}`
    const savedSessionId = localStorage.getItem(storageKey)
    
    if (savedSessionId) {
      currentSessionId.value = savedSessionId
      return savedSessionId
    }
    
    // 创建新会话
    const res = await codeRepositoryApi.createQASession(repoId.value, {
      session_name: `代码问答 - ${new Date().toLocaleString('zh-CN')}`
    })
    
    if (res.data && res.data.session_id) {
      currentSessionId.value = res.data.session_id
      // 保存到 localStorage
      localStorage.setItem(storageKey, res.data.session_id)
      return res.data.session_id
    }
    
    throw new Error('创建会话失败')
  } catch (error: any) {
    console.error('获取会话ID失败:', error)
    // 如果创建失败，生成一个临时ID（仅用于前端显示）
    const tempId = `temp_${Date.now()}`
    currentSessionId.value = tempId
    return tempId
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
    // 获取或创建会话ID
    const sessionId = await getOrCreateSessionId()
    
    const res = await codeRepositoryApi.codeQA({
      repository_id: repoId.value,
      question,
      session_id: sessionId
    })
    
    // 添加时间戳
    const qaResult = {
      ...res.data,
      created_at: new Date().toISOString()
    }
    qaHistory.value.push(qaResult)
    
    // 保存到 localStorage（作为备份）
    const storageKey = `qa_history_${repoId.value}_${sessionId}`
    try {
      localStorage.setItem(storageKey, JSON.stringify(qaHistory.value))
    } catch (e) {
      console.warn('保存到 localStorage 失败:', e)
    }
    
    // 滚动到底部并渲染 Mermaid
    await nextTick()
    setTimeout(() => {
      renderAllMermaidDiagrams()
      const el = qaHistoryRef.value || document.querySelector('.qa-history')
      if (el) {
        el.scrollTop = el.scrollHeight
      }
    }, 200)
  } catch (error: any) {
    console.error('问答失败:', error)
    ElMessage.error('问答失败')
  } finally {
    qaLoading.value = false
  }
}

// 格式化答案（使用 marked 渲染 Markdown）
const formatAnswer = (answer: string) => {
  if (!answer) return ''
  
  try {
    // 使用 marked 渲染 Markdown
    const html = marked.parse(answer) as string
    return html
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    // 降级处理：简单格式化
    return answer
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br/>')
      .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  }
}

// 渲染所有 Mermaid 图表
const renderAllMermaidDiagrams = async () => {
  if (!qaHistoryRef.value) return
  
  // 动态导入 Mermaid
  let mermaidModule: any = null
  try {
    mermaidModule = await import('mermaid')
  } catch (error) {
    console.warn('Mermaid 未安装，流程图渲染功能将不可用')
    return
  }
  
  if (!mermaidModule) return
  
  const mermaid = mermaidModule.default
  mermaid.initialize({ 
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      curve: 'basis'
    }
  })
  
  // 查找所有答案容器中的 Mermaid 代码块
  const answerContainers = qaHistoryRef.value.querySelectorAll('.answer-content')
  
  for (let containerIndex = 0; containerIndex < answerContainers.length; containerIndex++) {
    const container = answerContainers[containerIndex] as HTMLElement
    
    // 查找 Mermaid 代码块
    const mermaidBlocks = container.querySelectorAll('pre code.language-mermaid, pre code.lang-mermaid')
    
    // 如果没有找到，尝试查找包含 Mermaid 语法的代码块
    if (mermaidBlocks.length === 0) {
      const allCodeBlocks = container.querySelectorAll('pre code')
      for (const block of allCodeBlocks) {
        const text = block.textContent || ''
        if (text.match(/^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|gitgraph|journey|requirement)/m)) {
          mermaidBlocks.push(block as HTMLElement)
        }
      }
    }
    
    for (let i = 0; i < mermaidBlocks.length; i++) {
      const codeBlock = mermaidBlocks[i] as HTMLElement
      const mermaidCode = codeBlock.textContent || ''
      
      if (!mermaidCode.trim()) continue
      
      try {
        // 提取 Mermaid 代码
        let code = mermaidCode.trim()
        code = code.replace(/^```mermaid\n?/i, '').replace(/```\s*$/g, '').trim()
        
        // 修复常见的 Mermaid 语法错误
        code = fixMermaidCode(code)
        
        // 创建容器
        const mermaidContainer = document.createElement('div')
        mermaidContainer.className = 'mermaid-diagram-container'
        mermaidContainer.style.cssText = 'margin: 16px 0; padding: 16px; background: #fff; border-radius: 4px; border: 1px solid #e4e7ed; overflow-x: auto;'
        
        // 渲染 Mermaid
        const id = `mermaid-qa-${containerIndex}-${i}-${Date.now()}`
        const { svg } = await mermaid.render(id, code)
        
        mermaidContainer.innerHTML = svg
        
        // 替换代码块
        const preElement = codeBlock.parentElement
        if (preElement) {
          preElement.replaceWith(mermaidContainer)
        }
      } catch (error: any) {
        console.error('Mermaid 渲染失败:', error)
        // 保留原始代码块，但添加错误提示
        const preElement = codeBlock.parentElement as HTMLElement
        if (preElement) {
          preElement.style.cssText = 'padding: 12px; background: #fef0f0; border: 1px solid #fde2e2; border-radius: 4px; color: #f56c6c;'
          preElement.innerHTML = `<div style="font-weight: 600; margin-bottom: 8px;">⚠️ 流程图渲染失败</div><pre style="margin: 0; white-space: pre-wrap; font-size: 12px;">${codeBlock.textContent}</pre>`
        }
      }
    }
  }
}

// 修复 Mermaid 代码语法错误
const fixMermaidCode = (code: string): string => {
  if (!code) return code
  
  const lines = code.split('\n')
  const fixedLines: string[] = []
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim()
    if (!line) continue
    
    // 跳过注释行
    if (line.startsWith('#') || line.startsWith('//')) {
      continue
    }
    
    // 修复不完整的箭头
    if (line.includes('->') && !line.includes('-->')) {
      if (line.endsWith('->') || line.endsWith('-->')) {
        continue
      }
      line = line.replace(/ -> /g, ' --> ').replace(/->/g, ' --> ')
    }
    
    fixedLines.push(line)
  }
  
  let fixedCode = fixedLines.join('\n')
  
  // 确保有图表类型声明
  if (!fixedCode.match(/^(graph|sequenceDiagram|flowchart|classDiagram|stateDiagram|erDiagram|gantt|pie|gitgraph|journey|requirement)/)) {
    fixedCode = 'graph TD\n' + fixedCode
  }
  
  return fixedCode
}

// 返回
const goBack = () => {
  router.back()
}

// 根据文件路径查找文件
const findFileByPath = (filePath: string) => {
  if (!codeStructure.value?.files) {
    console.warn('代码结构文件列表为空')
    return null
  }
  
  // 标准化路径：移除开头的斜杠，统一使用正斜杠
  const normalizePath = (path: string) => {
    return path.replace(/^\/+/, '').replace(/\\/g, '/')
  }
  
  const normalizedTarget = normalizePath(filePath)
  console.log('查找文件 - 目标路径:', normalizedTarget)
  
  // 尝试多种匹配方式
  const file = codeStructure.value.files.find((f: any) => {
    const normalizedFile = normalizePath(f.file_path)
    
    // 1. 精确匹配
    if (normalizedFile === normalizedTarget) {
      console.log('精确匹配:', normalizedFile)
      return true
    }
    
    // 2. 文件名匹配（路径末尾）
    if (normalizedFile.endsWith(normalizedTarget)) {
      console.log('路径末尾匹配:', normalizedFile, '->', normalizedTarget)
      return true
    }
    
    // 3. 反向匹配（目标路径是文件路径的末尾）
    if (normalizedTarget.endsWith(normalizedFile)) {
      console.log('反向匹配:', normalizedTarget, '->', normalizedFile)
      return true
    }
    
    // 4. 文件名匹配（只比较文件名）
    const targetFileName = normalizedTarget.split('/').pop()
    const fileFileName = normalizedFile.split('/').pop()
    if (targetFileName && fileFileName && targetFileName === fileFileName) {
      // 如果文件名相同，进一步检查路径相似度
      const targetDir = normalizedTarget.substring(0, normalizedTarget.lastIndexOf('/'))
      const fileDir = normalizedFile.substring(0, normalizedFile.lastIndexOf('/'))
      if (targetDir.endsWith(fileDir) || fileDir.endsWith(targetDir)) {
        console.log('文件名匹配:', normalizedFile, '->', normalizedTarget)
        return true
      }
    }
    
    return false
  })
  
  if (!file) {
    console.warn('未找到匹配文件，前10个文件路径:', 
      codeStructure.value.files.slice(0, 10).map((f: any) => normalizePath(f.file_path))
    )
  }
  
  return file || null
}

// 处理路由查询参数（文件路径或符号）
const handleRouteQuery = async () => {
  const filePath = route.query.file as string
  const symbolName = route.query.symbol as string
  
  if (filePath) {
    // 如果有文件路径参数，切换到代码结构标签页并打开文件
    activeTab.value = 'structure'
    await loadStructure()
    
    // 等待代码结构加载完成后查找文件
    await nextTick()
    const file = findFileByPath(filePath)
    if (file) {
      viewFileDetail(file)
      // 自动加载文件内容
      await nextTick()
      await loadFileContent()
      // 清除查询参数，避免刷新时重复打开
      router.replace({ query: { ...route.query, file: undefined } })
    } else {
      ElMessage.warning(`未找到文件: ${decodeURIComponent(filePath)}`)
    }
  } else if (symbolName) {
    // 如果有符号参数，切换到代码结构标签页
    activeTab.value = 'structure'
    await loadStructure()
    // TODO: 实现符号定位功能
    ElMessage.info(`符号: ${decodeURIComponent(symbolName)}`)
  }
}

// 初始化
onMounted(async () => {
  await loadRepository()
  await loadSummary()
  
  // 处理路由查询参数
  await handleRouteQuery()
  
  // 加载问答历史记录
  await loadQAHistory()
})
</script>

<style scoped lang="scss">
.code-repository-detail {
  padding: 20px;
  font-size: 14px;

  .file-content-section {
    margin-top: 20px;

    .file-content-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;

      h4 {
        margin: 0;
      }
    }

    .file-content-wrapper {
      border: 1px solid #e4e7ed;
      border-radius: 4px;
      background: #f5f7fa;
      max-height: 600px;
      overflow: auto;

      .file-content {
        padding: 15px;
        background: #ffffff;

        .code-viewer {
          .code-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 8px;
            background: #f5f7fa;
            border-radius: 4px;
            flex-wrap: wrap;
            gap: 8px;

            .toolbar-left {
              display: flex;
              align-items: center;
              flex-wrap: wrap;
              gap: 8px;
              flex: 1;
            }

            .code-position {
              font-size: 12px;
              color: #409eff;
              font-family: 'Consolas', 'Monaco', monospace;
              font-weight: 500;
              padding: 4px 8px;
              background: #ecf5ff;
              border-radius: 4px;
            }
          }

          .code-container {
            position: relative;
          }

          pre.code-content {
            margin: 0;
            cursor: text;
            position: relative;
            padding: 10px;
            background: #fafafa;
            border: 1px solid #e4e7ed;
            border-radius: 4px;
            user-select: text;
            width: 100%;
            box-sizing: border-box;

            &:hover {
              border-color: #409eff;
            }

            &:active {
              border-color: #66b1ff;
            }

            code {
              display: block;
              white-space: pre;
              word-wrap: normal;
              font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
              font-size: 14px;
              line-height: 1.5;
              color: #303133;
              pointer-events: none; // 让点击事件穿透到 pre 元素
            }
          }
        }

        pre {
          margin: 0;
          padding: 0;
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 13px;
          line-height: 1.6;
          white-space: pre-wrap;
          word-wrap: break-word;

          code {
            display: block;
            color: #303133;
            background: transparent;
            padding: 0;
          }
        }
      }
    }
  }
  
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

  
  // 对话框样式
  :deep(.qa-dialog) {
    .el-dialog__body {
      padding: 0;
    }
  }

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 4px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .header-icon {
        font-size: 20px;
        color: #409EFF;
      }

      .header-title {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
      }
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }
  }

  .qa-container {
    display: flex;
    flex-direction: column;
    height: 70vh;
    min-height: 600px;
    background: #fafbfc;

    .qa-history {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      background: linear-gradient(to bottom, #fafbfc 0%, #f5f7fa 100%);
      
      // 自定义滚动条
      &::-webkit-scrollbar {
        width: 6px;
      }
      
      &::-webkit-scrollbar-track {
        background: transparent;
      }
      
      &::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 3px;
        
        &:hover {
          background: #a8a8a8;
        }
      }

      // 空状态
      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        padding: 40px;
        text-align: center;

        .empty-icon {
          margin-bottom: 20px;
          color: #c0c4cc;
        }

        .empty-title {
          margin: 0 0 12px 0;
          font-size: 20px;
          font-weight: 600;
          color: #303133;
        }

        .empty-description {
          margin: 0 0 24px 0;
          font-size: 14px;
          color: #909399;
        }

        .example-questions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          justify-content: center;
          max-width: 600px;

          .example-tag {
            cursor: pointer;
            transition: all 0.3s;
            padding: 8px 16px;
            font-size: 13px;

            &:hover {
              transform: translateY(-2px);
              box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
            }
          }
        }
      }

      // 消息气泡
      .message-bubble {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;
        animation: fadeIn 0.3s ease-in;

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .bubble-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          font-size: 18px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .user-avatar {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }

        .ai-avatar {
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          color: white;
        }

        .bubble-content {
          flex: 1;
          min-width: 0;
        }

        .bubble-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;

          .bubble-name {
            font-size: 13px;
            font-weight: 600;
            color: #606266;
          }

          .bubble-time {
            font-size: 12px;
            color: #c0c4cc;
          }
        }

        .bubble-text {
          line-height: 1.7;
          word-wrap: break-word;
        }
      }

      .question-bubble {
        .bubble-content {
          .bubble-text {
            padding: 12px 16px;
            background: white;
            border-radius: 12px 12px 12px 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            color: #303133;
            font-size: 14px;
          }
        }
      }

      .answer-bubble {
        .bubble-content {
          .bubble-text {
            padding: 16px;
            background: white;
            border-radius: 12px 12px 4px 12px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
            color: #303133;
            font-size: 14px;
          }
        }
      }

      // 加载状态
      .loading-bubble {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;

        .bubble-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          font-size: 18px;
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          color: white;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .typing-indicator {
          display: flex;
          gap: 4px;
          padding: 16px;
          background: white;
          border-radius: 12px 12px 4px 12px;
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);

          span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #c0c4cc;
            animation: typing 1.4s infinite;

            &:nth-child(2) {
              animation-delay: 0.2s;
            }

            &:nth-child(3) {
              animation-delay: 0.4s;
            }
          }

          @keyframes typing {
            0%, 60%, 100% {
              transform: translateY(0);
              opacity: 0.7;
            }
            30% {
              transform: translateY(-10px);
              opacity: 1;
            }
          }
        }
      }

      // Markdown 样式
      .answer-content {
        :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
          margin-top: 16px;
          margin-bottom: 10px;
          font-weight: 600;
          line-height: 1.4;
          color: #303133;
        }
        
        :deep(h1) { font-size: 20px; }
        :deep(h2) { font-size: 18px; }
        :deep(h3) { font-size: 16px; }
        :deep(h4) { font-size: 14px; }
        
        :deep(p) {
          margin: 10px 0;
          line-height: 1.8;
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
          padding: 3px 6px;
          background: #f1f2f3;
          border-radius: 4px;
          font-family: 'Consolas', 'Monaco', monospace;
          font-size: 0.9em;
          color: #e83e8c;
        }
        
        :deep(pre) {
          margin: 12px 0;
          padding: 16px;
          background: #282c34;
          border-radius: 8px;
          overflow-x: auto;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          
          code {
            padding: 0;
            background: transparent;
            color: #abb2bf;
          }
        }
        
        :deep(blockquote) {
          margin: 12px 0;
          padding: 12px 16px;
          border-left: 4px solid #409EFF;
          background: #ecf5ff;
          border-radius: 4px;
          color: #606266;
        }
        
        :deep(table) {
          width: 100%;
          border-collapse: collapse;
          margin: 12px 0;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          border-radius: 4px;
          overflow: hidden;
          
          th, td {
            padding: 10px 12px;
            border: 1px solid #e4e7ed;
          }
          
          th {
            background: #f5f7fa;
            font-weight: 600;
            color: #303133;
          }
          
          tr:hover {
            background: #fafafa;
          }
        }
        
        :deep(a) {
          color: #409EFF;
          text-decoration: none;
          transition: all 0.2s;
          
          &:hover {
            color: #66b1ff;
            text-decoration: underline;
          }
        }
        
        // Mermaid 图表样式
        :deep(.mermaid-diagram-container) {
          margin: 20px 0;
          padding: 20px;
          background: #fff;
          border-radius: 8px;
          border: 1px solid #e4e7ed;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
          overflow-x: auto;
          text-align: center;
          
          svg {
            max-width: 100%;
            height: auto;
          }
        }
      }

      .sources {
        margin-top: 16px;

        .sources-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;

          .source-tag {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            cursor: pointer;
            transition: all 0.2s;

            &:hover {
              transform: translateY(-1px);
              box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
          }
        }
      }
    }

    .qa-input-area {
      padding: 16px 24px;
      background: white;
      border-top: 1px solid #e4e7ed;
      box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);

      .input-wrapper {
        max-width: 1200px;
        margin: 0 auto;

        .question-input {
          margin-bottom: 12px;

          :deep(.el-textarea__inner) {
            border-radius: 8px;
            border: 1px solid #dcdfe6;
            transition: all 0.3s;
            font-size: 14px;
            line-height: 1.6;

            &:focus {
              border-color: #409EFF;
              box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
            }
          }
        }

        .input-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .input-tips {
            display: flex;
            align-items: center;
            gap: 4px;
            color: #909399;
          }

          .send-button {
            min-width: 100px;
            border-radius: 8px;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
            transition: all 0.3s;

            &:hover:not(:disabled) {
              transform: translateY(-1px);
              box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
            }

            &:active:not(:disabled) {
              transform: translateY(0);
            }
          }
        }
      }
    }
  }
}

// 代码解释对话框样式
.explanation-content {
  .explanation-header {
    display: flex;
    align-items: center;
    margin-bottom: 16px;
  }
  
  .code-section {
    margin-bottom: 20px;
    
    h4 {
      margin-bottom: 12px;
      color: #303133;
      font-size: 16px;
      font-weight: 600;
    }
    
    .code-block {
      background: #f5f7fa;
      border: 1px solid #e4e7ed;
      border-radius: 4px;
      padding: 16px;
      overflow-x: auto;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
      margin: 0;
      
      code {
        color: #303133;
      }
    }
  }
  
  .explanation-section {
    h4 {
      margin-bottom: 12px;
      color: #303133;
      font-size: 16px;
      font-weight: 600;
    }
    
    .explanation-text {
      line-height: 1.8;
      color: #606266;
      
      p {
        margin: 12px 0;
      }
      
      h2 {
        font-size: 20px;
        margin: 20px 0 12px;
        color: #303133;
      }
      
      h3 {
        font-size: 18px;
        margin: 16px 0 10px;
        color: #303133;
      }
      
      h4 {
        font-size: 16px;
        margin: 14px 0 8px;
        color: #303133;
      }
      
      code {
        background: #f5f7fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 13px;
      }
      
      pre {
        background: #f5f7fa;
        padding: 12px;
        border-radius: 4px;
        overflow-x: auto;
        margin: 12px 0;
        
        code {
          background: transparent;
          padding: 0;
        }
      }
    }
  }
}

.context-preview {
  margin: 0;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  white-space: pre-wrap;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
