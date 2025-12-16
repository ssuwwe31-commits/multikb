<template>
  <div class="exports-page">
    <el-card>
      <template #header>
        <span>导出管理</span>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 导出任务列表 -->
        <el-tab-pane label="导出任务" name="tasks">
          <div class="task-list">
            <div class="task-query" style="margin-bottom: 20px">
              <el-input
                v-model="taskIdInput"
                placeholder="输入任务ID查询"
                style="width: 200px; margin-right: 12px"
                @keyup.enter="queryTask"
              >
                <template #append>
                  <el-button type="primary" @click="queryTask" :loading="taskLoading">查询</el-button>
                </template>
              </el-input>
            </div>

            <el-table :data="tasks" v-loading="loading" stripe>
              <el-table-column prop="task_id" label="任务ID" width="100" />
              <el-table-column prop="export_type" label="导出类型" width="150">
                <template #default="{ row }">
                  {{ getExportTypeText(row.export_type) }}
                </template>
              </el-table-column>
              <el-table-column prop="export_format" label="格式" width="100" />
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)">
                    {{ getStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="file_size" label="文件大小" width="120">
                <template #default="{ row }">
                  {{ row.file_size ? formatFileSize(row.file_size) : '—' }}
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="180">
                <template #default="{ row }">
                  {{ formatDateTime(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column prop="completed_at" label="完成时间" width="180">
                <template #default="{ row }">
                  {{ row.completed_at ? formatDateTime(row.completed_at) : '—' }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.status === 'completed' && row.download_url"
                    type="primary"
                    size="small"
                    @click="handleDownloadByUrl(row)"
                  >
                    下载
                  </el-button>
                  <el-button
                    v-else-if="row.status === 'completed'"
                    type="primary"
                    size="small"
                    @click="handleDownload(row)"
                  >
                    下载
                  </el-button>
                  <el-button
                    v-if="row.status === 'processing'"
                    type="info"
                    size="small"
                    @click="refreshTask(row)"
                  >
                    刷新
                  </el-button>
                  <el-button
                    type="danger"
                    size="small"
                    @click="removeTask(row)"
                  >
                    移除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="tasks.length === 0 && !loading" description="暂无任务，请先创建导出任务" />
          </div>
        </el-tab-pane>

        <!-- 导出知识库 -->
        <el-tab-pane label="导出知识库" name="kb">
          <el-form :model="kbExportForm" label-width="120px" style="max-width: 600px">
            <el-form-item label="选择知识库" required>
              <el-select v-model="kbExportForm.kb_id" placeholder="请选择知识库" style="width: 100%">
                <el-option
                  v-for="kb in knowledgeBases"
                  :key="kb.id"
                  :label="kb.name"
                  :value="kb.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="导出格式" required>
              <el-radio-group v-model="kbExportForm.format">
                <el-radio label="markdown">Markdown</el-radio>
                <el-radio label="json">JSON</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="包含选项">
              <el-checkbox v-model="kbExportForm.include_documents">包含文档</el-checkbox>
              <el-checkbox v-model="kbExportForm.include_chunks">包含分块</el-checkbox>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleExportKB" :loading="exporting">
                开始导出
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 导出文档 -->
        <el-tab-pane label="导出文档" name="doc">
          <el-form :model="docExportForm" label-width="120px" style="max-width: 600px">
            <el-form-item label="选择文档" required>
              <el-select
                v-model="docExportForm.doc_ids"
                multiple
                placeholder="请选择文档"
                style="width: 100%"
                filterable
              >
                <el-option
                  v-for="doc in documents"
                  :key="doc.id"
                  :label="doc.title || doc.file_name"
                  :value="doc.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="导出格式" required>
              <el-radio-group v-model="docExportForm.format">
                <el-radio label="markdown">Markdown</el-radio>
                <el-radio label="json">JSON</el-radio>
                <el-radio label="original">原始文档</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="包含选项" v-if="docExportForm.format !== 'original'">
              <el-checkbox v-model="docExportForm.include_chunks">包含分块</el-checkbox>
              <el-checkbox v-model="docExportForm.include_images">包含图片</el-checkbox>
            </el-form-item>
            <el-form-item v-if="docExportForm.format === 'original'">
              <el-alert
                type="info"
                :closable="false"
                show-icon
              >
                <template #title>
                  <span>将直接导出原始文档文件，不进行任何转换</span>
                </template>
              </el-alert>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleExportDoc" :loading="exporting">
                开始导出
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 导出问答历史 -->
        <el-tab-pane label="导出问答历史" name="qa">
          <div class="export-instructions">
            <div class="instructions-header">
              <el-icon class="header-icon"><InfoFilled /></el-icon>
              <span class="header-title">导出说明</span>
            </div>
            <div class="instructions-content">
              <div class="instruction-item">
                <el-icon class="item-icon"><CircleCheck /></el-icon>
                <span><strong>不选择会话</strong>：导出所有会话的问答历史</span>
              </div>
              <div class="instruction-item">
                <el-icon class="item-icon"><CircleCheck /></el-icon>
                <span><strong>选择会话</strong>：仅导出指定会话的问答历史</span>
              </div>
              <div class="instruction-item">
                <el-icon class="item-icon"><CircleCheck /></el-icon>
                <span><strong>日期范围</strong>：可筛选指定时间段的问答记录（可选）</span>
              </div>
              <div class="instruction-item">
                <el-icon class="item-icon"><CircleCheck /></el-icon>
                <span><strong>导出格式</strong>：JSON（完整数据）或 CSV（表格数据）</span>
              </div>
            </div>
          </div>
          
          <el-form :model="qaExportForm" label-width="120px" style="max-width: 600px">
            <el-form-item label="导出格式" required>
              <el-radio-group v-model="qaExportForm.format">
                <el-radio label="json">JSON（推荐，包含完整信息）</el-radio>
                <el-radio label="csv">CSV（表格格式）</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="选择会话">
              <el-select
                v-model="qaExportForm.session_id"
                placeholder="不选择则导出所有会话"
                clearable
                filterable
                style="width: 100%"
                :loading="sessionsLoading"
                @visible-change="handleSessionDropdownOpen"
              >
                <el-option
                  v-for="session in qaSessions"
                  :key="session.session_id || session.id"
                  :label="getSessionLabel(session)"
                  :value="session.session_id || session.id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span>{{ getSessionLabel(session) }}</span>
                    <el-tag size="small" type="info" style="margin-left: 8px">
                      {{ session.question_count || 0 }} 个问题
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
              <div style="font-size: 12px; color: #909399; margin-top: 4px">
                {{ qaExportForm.session_id ? '将仅导出选中会话的问答历史' : '将导出所有会话的问答历史' }}
              </div>
            </el-form-item>
            
            <el-form-item label="日期范围">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                style="width: 100%"
                :shortcuts="dateShortcuts"
                @change="handleDateRangeChange"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 4px">
                {{ dateRange ? `将导出 ${dateRange[0]} 至 ${dateRange[1]} 期间的问答记录` : '不限制日期，导出所有时间的问答记录' }}
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="handleExportQA" :loading="exporting" size="large">
                开始导出
              </el-button>
              <el-button @click="handleResetQAForm" style="margin-left: 12px">重置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled, CircleCheck } from '@element-plus/icons-vue'
import {
  getExportTasks,
  getExportTask,
  deleteExportTask,
  downloadExportFile,
  exportKnowledgeBase,
  exportDocument,
  batchExportDocuments,
  exportQAHistory
} from '@/api/modules/exports'
import { getKnowledgeBases } from '@/api/modules/knowledge-bases'
import { getDocuments } from '@/api/modules/documents'
import { formatFileSize, formatDateTime } from '@/utils/format'
import type { KnowledgeBase, Document } from '@/types'
import { getQASessions } from '@/api/modules/qa'

const loading = ref(false)
const exporting = ref(false)
const taskLoading = ref(false)
const activeTab = ref('tasks')
const tasks = ref<any[]>([])
const knowledgeBases = ref<KnowledgeBase[]>([])
const documents = ref<Document[]>([])
const dateRange = ref<[string, string] | null>(null)
const taskIdInput = ref('')

// QA导出相关
const qaSessions = ref<any[]>([])
const sessionsLoading = ref(false)
// 日期快捷选项（每次点击时动态计算）
const dateShortcuts = [
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end] as [Date, Date]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end] as [Date, Date]
    }
  },
  {
    text: '最近90天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
      return [start, end] as [Date, Date]
    }
  },
  {
    text: '最近一年',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 365)
      return [start, end] as [Date, Date]
    }
  }
]

const kbExportForm = ref({
  kb_id: null as number | null,
  format: 'markdown',
  include_documents: true,
  include_chunks: false
})

const docExportForm = ref({
  doc_ids: [] as number[],
  format: 'markdown',
  include_chunks: true,
  include_images: false,
  export_original: false
})

const qaExportForm = ref({
  format: 'json',
  session_id: null as string | null,
  start_date: '',
  end_date: ''
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await getExportTasks({ limit: 100 })
    // 后端返回格式: { code: 0, message: "ok", data: { list: [], total: 0 } }
    if (res && typeof res === 'object') {
      if (res.code === 0 && res.data) {
        tasks.value = res.data.list || res.data.items || []
      } else if (res.data) {
        // 兼容没有 code 字段的格式
        tasks.value = res.data.list || res.data.items || []
      } else if (Array.isArray(res)) {
        // 兼容直接返回数组的格式
        tasks.value = res
      } else {
        tasks.value = []
      }
    } else {
      tasks.value = []
    }
  } catch (error: any) {
    console.error('加载导出任务列表失败:', error)
    tasks.value = []
    // 不显示错误消息，因为可能是正常的（没有任务）
  } finally {
    loading.value = false
  }
}

const queryTask = async () => {
  if (!taskIdInput.value) {
    ElMessage.warning('请输入任务ID')
    return
  }

  const taskId = Number(taskIdInput.value)
  if (isNaN(taskId)) {
    ElMessage.warning('任务ID必须是数字')
    return
  }

  taskLoading.value = true
  try {
    const res = await getExportTask(taskId)
    const data = res?.data || res
    // 检查任务是否已存在
    const index = tasks.value.findIndex(t => t.task_id === taskId)
    if (index >= 0) {
      tasks.value[index] = data
    } else {
      tasks.value.unshift(data)
    }
    ElMessage.success('查询成功')
    taskIdInput.value = ''
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '查询任务失败')
  } finally {
    taskLoading.value = false
  }
}

const removeTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个导出任务吗？删除后将无法恢复。',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用后端API删除任务（软删除+硬删除同时执行）
    await deleteExportTask(task.task_id)
    
    // 从前端列表中移除
    const index = tasks.value.findIndex(t => t.task_id === task.task_id)
    if (index >= 0) {
      tasks.value.splice(index, 1)
    }
    
    ElMessage.success('删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || error.message || '删除失败')
    }
  }
}

const loadKnowledgeBases = async () => {
  try {
    const res = await getKnowledgeBases({ page: 1, size: 1000 })
    // 后端返回格式: { code: 0, message: "ok", data: { list: [], total: 0 } }
    // 响应拦截器已经返回了 response.data，所以 res 就是响应数据本身
    if (res && typeof res === 'object') {
      if (res.code === 0 && res.data) {
        knowledgeBases.value = res.data.list || res.data.items || []
      } else if (res.data) {
        // 兼容没有 code 字段的格式
        knowledgeBases.value = res.data.list || res.data.items || []
      } else if (Array.isArray(res)) {
        // 兼容直接返回数组的格式
        knowledgeBases.value = res
      } else {
        knowledgeBases.value = []
      }
    } else {
      knowledgeBases.value = []
    }
  } catch (error: any) {
    console.error('加载知识库列表失败:', error)
    knowledgeBases.value = []
    ElMessage.error(error.response?.data?.detail || error.message || '加载知识库列表失败')
  }
}

const loadDocuments = async () => {
  try {
    const res = await getDocuments({ page: 1, size: 1000 })
    // 后端返回格式: { code: 0, message: "ok", data: { list: [], total: 0 } }
    // 响应拦截器已经返回了 response.data，所以 res 就是响应数据本身
    if (res && typeof res === 'object') {
      if (res.code === 0 && res.data) {
        documents.value = res.data.list || res.data.items || []
      } else if (res.data) {
        // 兼容没有 code 字段的格式
        documents.value = res.data.list || res.data.items || []
      } else if (Array.isArray(res)) {
        // 兼容直接返回数组的格式
        documents.value = res
      } else {
        documents.value = []
      }
    } else {
      documents.value = []
    }
  } catch (error: any) {
    console.error('加载文档列表失败:', error)
    documents.value = []
    ElMessage.error(error.response?.data?.detail || error.message || '加载文档列表失败')
  }
}

const handleExportKB = async () => {
  if (!kbExportForm.value.kb_id) {
    ElMessage.warning('请选择知识库')
    return
  }

  exporting.value = true
  try {
    const res = await exportKnowledgeBase(kbExportForm.value.kb_id, {
      format: kbExportForm.value.format,
      include_documents: kbExportForm.value.include_documents,
      include_chunks: kbExportForm.value.include_chunks
    })
    const data = res?.data || res
    ElMessage.success(`导出任务已创建，任务ID: ${data.task_id}`)
    // 自动查询任务状态
    taskIdInput.value = String(data.task_id)
    await queryTask()
    activeTab.value = 'tasks'
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

const handleExportDoc = async () => {
  if (docExportForm.value.doc_ids.length === 0) {
    ElMessage.warning('请选择至少一个文档')
    return
  }

  exporting.value = true
  try {
    const isOriginal = docExportForm.value.format === 'original'
    let res: any
    if (docExportForm.value.doc_ids.length === 1) {
      res = await exportDocument(docExportForm.value.doc_ids[0], {
        format: isOriginal ? 'original' : docExportForm.value.format,
        include_chunks: isOriginal ? false : docExportForm.value.include_chunks,
        include_images: isOriginal ? false : docExportForm.value.include_images,
        export_original: isOriginal
      })
    } else {
      res = await batchExportDocuments({
        document_ids: docExportForm.value.doc_ids,
        format: isOriginal ? 'original' : docExportForm.value.format,
        include_chunks: isOriginal ? false : docExportForm.value.include_chunks,
        include_images: isOriginal ? false : docExportForm.value.include_images,
        export_original: isOriginal
      })
    }
    const data = res?.data || res
    if (data.tasks && Array.isArray(data.tasks)) {
      // 批量导出返回任务列表
      data.tasks.forEach((t: any) => {
        const index = tasks.value.findIndex(task => task.task_id === t.task_id)
        if (index >= 0) {
          tasks.value[index] = t
        } else {
          tasks.value.unshift(t)
        }
      })
      ElMessage.success(`已创建 ${data.tasks.length} 个导出任务`)
    } else if (data.task_id) {
      // 单个导出返回任务ID
      taskIdInput.value = String(data.task_id)
      await queryTask()
      ElMessage.success('导出任务已创建')
    } else {
      ElMessage.success('导出任务已创建')
    }
    activeTab.value = 'tasks'
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

const loadQASessions = async () => {
  if (sessionsLoading.value || qaSessions.value.length > 0) {
    return // 已加载或正在加载中
  }
  
  sessionsLoading.value = true
  try {
    const res = await getQASessions({ page: 1, size: 100 })
    const data = res?.data || res
    if (data?.sessions && Array.isArray(data.sessions)) {
      qaSessions.value = data.sessions
    } else if (Array.isArray(data)) {
      qaSessions.value = data
    } else {
      qaSessions.value = []
    }
  } catch (error: any) {
    console.error('加载会话列表失败:', error)
    qaSessions.value = []
  } finally {
    sessionsLoading.value = false
  }
}

const handleSessionDropdownOpen = (visible: boolean) => {
  if (visible && qaSessions.value.length === 0) {
    loadQASessions()
  }
}

const getSessionLabel = (session: any): string => {
  if (session.session_name) {
    return session.session_name
  }
  if (session.title) {
    return session.title
  }
  if (session.session_id) {
    return `会话 ${session.session_id.slice(0, 8)}...`
  }
  return `会话 ${session.id || '未知'}`
}

const handleExportQA = async () => {
  // 验证表单
  if (!qaExportForm.value.start_date && !qaExportForm.value.end_date && dateRange.value) {
    // 如果日期范围有值但表单字段为空，重新同步
    handleDateRangeChange(dateRange.value)
  }
  
  exporting.value = true
  try {
    // ✅ 直接使用session_id字符串（后端已支持）
    const res = await exportQAHistory({
      format: qaExportForm.value.format,
      session_id: qaExportForm.value.session_id || undefined,
      start_date: qaExportForm.value.start_date || undefined,
      end_date: qaExportForm.value.end_date || undefined
    })
    const data = res?.data || res
    ElMessage.success(`导出任务已创建，任务ID: ${data.task_id}`)
    // 自动查询任务状态
    taskIdInput.value = String(data.task_id)
    await queryTask()
    activeTab.value = 'tasks'
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

const handleResetQAForm = () => {
  qaExportForm.value = {
    format: 'json',
    session_id: null,
    start_date: '',
    end_date: ''
  }
  dateRange.value = null
  ElMessage.success('表单已重置')
}

const handleDateRangeChange = (dates: [string, string] | null) => {
  if (dates) {
    qaExportForm.value.start_date = dates[0]
    qaExportForm.value.end_date = dates[1]
  } else {
    qaExportForm.value.start_date = ''
    qaExportForm.value.end_date = ''
  }
}

const handleDownload = async (task: any) => {
  try {
    const blob = await downloadExportFile(task.task_id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `export_${task.task_id}.${task.export_format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '下载失败')
  }
}

const handleDownloadByUrl = (task: any) => {
  if (task.download_url) {
    window.open(task.download_url, '_blank')
  } else {
    handleDownload(task)
  }
}

const refreshTask = async (task: any) => {
  try {
    const res = await getExportTask(task.task_id)
    const data = res?.data || res
    // 更新任务状态
    const index = tasks.value.findIndex(t => t.task_id === task.task_id)
    if (index >= 0) {
      tasks.value[index] = data
    }
    if (data.status === 'completed') {
      ElMessage.success('导出完成')
    }
  } catch (error: any) {
    ElMessage.error('刷新任务状态失败')
  }
}

const getExportTypeText = (type: string) => {
  const texts: Record<string, string> = {
    knowledge_base: '知识库',
    document: '文档',
    qa_history: '问答历史'
  }
  return texts[type] || type
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    completed: 'success',
    processing: 'warning',
    failed: 'danger',
    pending: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    completed: '已完成',
    processing: '处理中',
    failed: '失败',
    pending: '待处理'
  }
  return texts[status] || status
}

onMounted(() => {
  loadTasks()
  loadKnowledgeBases()
  loadDocuments()
})
</script>

<style lang="scss" scoped>
.exports-page {
  :deep(.el-card) {
    background: rgba(6, 12, 24, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.9);
    
    .el-card__header {
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      color: rgba(255, 255, 255, 0.95);
      font-size: 18px;
      font-weight: 600;
    }
    
    .el-card__body {
      color: rgba(255, 255, 255, 0.85);
    }
  }
  
  .task-list {
    margin-top: 20px;
  }

  // 深色主题的标签页样式
  :deep(.el-tabs) {
    .el-tabs__header {
      margin-bottom: 20px;
    }

    .el-tabs__nav-wrap::after {
      background-color: rgba(255, 255, 255, 0.2);
    }

    .el-tabs__item {
      color: rgba(255, 255, 255, 0.6);
      font-size: 15px;
      font-weight: 500;
      padding: 0 20px;
      height: 48px;
      line-height: 48px;
      transition: all 0.3s;

      &:hover {
        color: #409eff;
      }

      &.is-active {
        color: #409eff;
        font-weight: 600;
      }
    }

    .el-tabs__active-bar {
      background-color: #409eff;
      height: 3px;
    }
  }

  // 表单样式
  :deep(.el-form-item__label) {
    color: #e4e7ed;
    font-weight: 500;
  }

  :deep(.el-input__inner),
  :deep(.el-textarea__inner) {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.2);
    color: #e4e7ed;

    &::placeholder {
      color: rgba(255, 255, 255, 0.4);
    }

    &:focus {
      border-color: #409eff;
    }
  }

  :deep(.el-select) {
    .el-input__inner {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.2);
      color: #e4e7ed;
    }
  }

  :deep(.el-radio__label),
  :deep(.el-checkbox__label) {
    color: #e4e7ed;
  }

  :deep(.el-date-editor) {
    .el-input__inner {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.2);
      color: #e4e7ed;
    }
  }

  // 表格样式
  :deep(.el-table) {
    background: transparent !important;
    color: #e4e7ed;
    
    .el-table__body-wrapper {
      background: transparent !important;
    }
    
    .el-table__row {
      background-color: rgba(255, 255, 255, 0.02) !important;
      
      &:hover {
        background-color: rgba(64, 158, 255, 0.15) !important;
        
        td {
          background-color: transparent !important;
        }
      }
    }

    .el-table__header {
      th {
        background: rgba(30, 35, 50, 0.8) !important;
        color: #8fa8d0 !important;
        border-bottom: 2px solid rgba(64, 158, 255, 0.3);
        font-weight: 500 !important;
        font-size: 15px !important;
        
        .cell {
          color: #b8d4f0 !important;
          font-weight: 500;
          font-size: 15px !important;
        }
      }
    }

    .el-table__body {
      tr {
        background: rgba(255, 255, 255, 0.02) !important;
        
        &:hover {
          background: rgba(64, 158, 255, 0.15) !important;
          cursor: pointer;
          
          td {
            background-color: transparent !important;
            
            .cell {
              color: #ffffff !important;
            }
          }
        }
      }

      td {
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        color: #ffffff;
        background-color: transparent !important;
        
        .cell {
          color: #ffffff;
          font-weight: 400;
          font-size: 15px;
        }
      }
    }

    &::before {
      background-color: rgba(255, 255, 255, 0.2) !important;
    }

    .el-table__inner-wrapper::before {
      background-color: rgba(255, 255, 255, 0.2);
    }
  }

  // 按钮样式
  :deep(.el-button) {
    font-size: 15px;
    
    &:not(.el-button--primary) {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.2);
      color: #e4e7ed;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: #409eff;
        color: #409eff;
      }
    }

    &.el-button--primary {
      background: #409eff;
      border-color: #409eff;
      color: #ffffff;

      &:hover {
        background: #66b1ff;
        border-color: #66b1ff;
      }
    }
  }
  
  /* 科技感导出说明框 */
  .export-instructions {
    margin-bottom: 24px;
    max-width: 600px;
    background: linear-gradient(135deg, rgba(6, 12, 24, 0.95) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(64, 158, 255, 0.3);
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.4),
      0 0 0 1px rgba(64, 158, 255, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(10px);
    
    /* 科技感光效 */
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(64, 158, 255, 0.5) 50%, 
        transparent 100%);
      animation: shimmer 3s infinite;
    }
    
    &::after {
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: radial-gradient(circle, rgba(64, 158, 255, 0.05) 0%, transparent 70%);
      pointer-events: none;
    }
    
    .instructions-header {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(64, 158, 255, 0.2);
      
      .header-icon {
        font-size: 20px;
        color: #409eff;
        margin-right: 10px;
        filter: drop-shadow(0 0 4px rgba(64, 158, 255, 0.5));
      }
      
      .header-title {
        font-size: 16px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.95);
        letter-spacing: 0.5px;
      }
    }
    
    .instructions-content {
      display: flex;
      flex-direction: column;
      gap: 12px;
      
      .instruction-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 8px 0;
        color: rgba(255, 255, 255, 0.85);
        font-size: 14px;
        line-height: 1.6;
        transition: all 0.3s ease;
        
        &:hover {
          color: rgba(255, 255, 255, 0.95);
          transform: translateX(4px);
        }
        
        .item-icon {
          font-size: 16px;
          color: #409eff;
          margin-top: 2px;
          flex-shrink: 0;
          filter: drop-shadow(0 0 3px rgba(64, 158, 255, 0.4));
        }
        
        strong {
          color: rgba(255, 255, 255, 0.95);
          font-weight: 600;
        }
      }
    }
  }
  
  @keyframes shimmer {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(100%);
    }
  }
}
</style>
