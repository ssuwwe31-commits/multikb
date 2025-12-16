<template>
  <div class="failures-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>失败任务中心</span>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="任务类型">
            <el-select v-model="filterForm.task_type" placeholder="全部" clearable style="width: 150px">
              <el-option label="文档任务" value="document" />
              <el-option label="图片任务" value="image" />
            </el-select>
          </el-form-item>
          <el-form-item label="知识库">
            <el-select
              v-model="filterForm.knowledge_base_id"
              placeholder="全部"
              clearable
              filterable
              style="width: 200px"
            >
              <el-option
                v-for="kb in knowledgeBases"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleFilter">筛选</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 批量操作栏 -->
      <div class="batch-actions" v-if="selectedTasks.length > 0">
        <el-alert type="info" :closable="false">
          <template #default>
            <span>已选择 {{ selectedTasks.length }} 个任务</span>
            <el-button
              type="primary"
              size="small"
              style="margin-left: 16px"
              @click="handleBatchRetry"
            >
              批量重试
            </el-button>
          </template>
        </el-alert>
      </div>

      <!-- 任务列表 -->
      <el-table
        v-loading="loading"
        :data="tasks"
        @selection-change="handleSelectionChange"
        stripe
        border
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="task_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.task_type === 'document' ? 'primary' : 'success'">
              {{ row.task_type === 'document' ? '文档' : '图片' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
        <el-table-column prop="retry_count" label="重试次数" width="100" />
        <el-table-column prop="last_processed_at" label="最后处理时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.last_processed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleRetry(row)"
              :loading="retryingTasks.has(row.id)"
            >
              重试
            </el-button>
            <el-button
              size="small"
              @click="handleViewDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFailureTasks, retryTask, batchRetryTasks } from '@/api/modules/tasks'
import { getKnowledgeBases } from '@/api/modules/knowledge-bases'
import { formatDateTime } from '@/utils/format'
import { useRouter } from 'vue-router'

const router = useRouter()

const loading = ref(false)
const tasks = ref<any[]>([])
const selectedTasks = ref<any[]>([])
const retryingTasks = ref(new Set<number>())
const knowledgeBases = ref<any[]>([])

const filterForm = ref({
  task_type: undefined as 'document' | 'image' | undefined,
  knowledge_base_id: undefined as number | undefined
})

const pagination = ref({
  page: 1,
  size: 20,
  total: 0
})

const getStatusTagType = (status: string) => {
  const statusMap: Record<string, string> = {
    'failed': 'danger',
    'processing': 'warning',
    'pending': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'failed': '失败',
    'processing': '处理中',
    'pending': '待处理'
  }
  return statusMap[status] || status
}

const loadKnowledgeBases = async () => {
  try {
    const res = await getKnowledgeBases({ page: 1, size: 100 })
    const data = res?.data ?? {}
    knowledgeBases.value = data.list ?? data.items ?? []
  } catch (error) {
    console.error('加载知识库列表失败:', error)
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await getFailureTasks({
      task_type: filterForm.value.task_type,
      knowledge_base_id: filterForm.value.knowledge_base_id,
      page: pagination.value.page,
      size: pagination.value.size
    })
    const data = res.data || res
    tasks.value = data.tasks || []
    pagination.value.total = data.total || 0
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || '加载失败任务列表失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  pagination.value.page = 1
  loadTasks()
}

const handleReset = () => {
  filterForm.value = {
    task_type: undefined,
    knowledge_base_id: undefined
  }
  handleFilter()
}

const handleSelectionChange = (selection: any[]) => {
  selectedTasks.value = selection
}

const handleRetry = async (task: any) => {
  try {
    await ElMessageBox.confirm(`确定要重试任务 "${task.filename}" 吗？`, '提示', {
      type: 'warning'
    })
    
    retryingTasks.value.add(task.id)
    try {
      await retryTask(task.id, task.task_type)
      ElMessage.success('重试任务已启动')
      await loadTasks()
    } finally {
      retryingTasks.value.delete(task.id)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.message || error?.message || '重试失败')
    }
  }
}

const handleBatchRetry = async () => {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请选择要重试的任务')
    return
  }
  
  // 按任务类型分组
  const tasksByType = selectedTasks.value.reduce((acc, task) => {
    if (!acc[task.task_type]) {
      acc[task.task_type] = []
    }
    acc[task.task_type].push(task.id)
    return acc
  }, {} as Record<string, number[]>)
  
  try {
    await ElMessageBox.confirm(`确定要批量重试 ${selectedTasks.value.length} 个任务吗？`, '提示', {
      type: 'warning'
    })
    
    // 按类型分别批量重试
    for (const [taskType, taskIds] of Object.entries(tasksByType)) {
      await batchRetryTasks({
        task_ids: taskIds,
        task_type: taskType as 'document' | 'image'
      })
    }
    
    ElMessage.success('批量重试已启动')
    selectedTasks.value = []
    await loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.message || error?.message || '批量重试失败')
    }
  }
}

const handleViewDetail = (task: any) => {
  if (task.task_type === 'document' && task.document_id) {
    router.push(`/documents/${task.document_id}`)
  } else if (task.task_type === 'image' && task.document_id) {
    router.push(`/documents/${task.document_id}?tab=images`)
  } else {
    ElMessage.warning('无法查看详情')
  }
}

onMounted(() => {
  loadKnowledgeBases()
  loadTasks()
})
</script>

<style scoped>
.failures-page {
  padding: 20px;
}

.filter-bar {
  margin-bottom: 16px;
}

.batch-actions {
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
