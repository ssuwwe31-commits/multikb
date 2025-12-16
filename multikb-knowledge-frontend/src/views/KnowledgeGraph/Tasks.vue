<template>
  <div class="extraction-tasks-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>提取任务列表</span>
          <div class="header-actions">
            <el-select
              v-model="selectedKnowledgeBase"
              placeholder="选择知识库"
              style="width: 200px; margin-right: 10px"
              @change="handleKnowledgeBaseChange"
            >
              <el-option
                v-for="kb in knowledgeBases"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
            <el-button @click="loadTasks" :loading="loading" :disabled="!selectedKnowledgeBase">刷新</el-button>
          </div>
        </div>
      </template>

      <div v-if="!selectedKnowledgeBase" class="empty-state">
        <el-empty description="请选择一个知识库以查看任务列表" />
      </div>

      <div v-else>
        <el-table
          :data="tasks"
          v-loading="loading"
          style="width: 100%"
          stripe
          border
        >
          <el-table-column prop="id" label="任务ID" width="80" />
          <el-table-column prop="document_id" label="文档ID" width="100">
            <template #default="{ row }">
              {{ row.document_id || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="total_entities" label="实体数" width="100" />
          <el-table-column prop="total_relationships" label="关系数" width="100" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="completed_at" label="完成时间" width="180">
            <template #default="{ row }">
              {{ row.completed_at ? formatDateTime(row.completed_at) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button
                type="danger"
                size="small"
                @click="handleDeleteTask(row.id)"
                :loading="deletingTaskId === row.id"
              >
                删除
              </el-button>
              <el-button
                type="primary"
                size="small"
                @click="handleRegenerateTask(row.id)"
                :loading="regeneratingTaskId === row.id"
                :disabled="!row.document_id"
              >
                重新生成
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
          style="margin-top: 20px; justify-content: flex-end"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getKnowledgeBases } from '@/api/modules/knowledge-bases'
import {
  listExtractionTasks,
  deleteExtractionTask,
  regenerateExtractionTask,
  type ExtractionTask
} from '@/api/modules/knowledge-graph'
import type { KnowledgeBase } from '@/types'

const loading = ref(false)
const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKnowledgeBase = ref<number>()
const tasks = ref<ExtractionTask[]>([])
const pagination = ref({
  page: 1,
  size: 20,
  total: 0
})
const deletingTaskId = ref<number | null>(null)
const regeneratingTaskId = ref<number | null>(null)

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    console.log('[任务列表页面] 开始加载知识库列表')
    const res = await getKnowledgeBases({ page: 1, size: 100 })
    knowledgeBases.value = res.data?.list || res.data?.items || []
    console.log(`[任务列表页面] 知识库列表加载成功: 共${knowledgeBases.value.length}个`)
  } catch (error: any) {
    console.error('[任务列表页面] 加载知识库列表失败:', error)
    ElMessage.error('加载知识库列表失败: ' + (error.message || '未知错误'))
  }
}

// 知识库变化处理
const handleKnowledgeBaseChange = () => {
  console.log(`[任务列表页面] 知识库变更: ID=${selectedKnowledgeBase.value}`)
  pagination.value.page = 1
  loadTasks()
}

// 加载任务列表
const loadTasks = async () => {
  if (!selectedKnowledgeBase.value) {
    console.warn('[任务列表页面] 未选择知识库，无法加载任务列表')
    return
  }

  console.log(`[任务列表页面] 开始加载任务列表: 知识库ID=${selectedKnowledgeBase.value}, 页码=${pagination.value.page}, 每页=${pagination.value.size}`)
  loading.value = true
  try {
    const res = await listExtractionTasks({
      knowledge_base_id: selectedKnowledgeBase.value,
      page: pagination.value.page,
      size: pagination.value.size
    })
    tasks.value = res.data.tasks || []
    pagination.value.total = res.data.total || 0
    console.log(`[任务列表页面] 加载成功: 总数=${pagination.value.total}, 当前页任务数=${tasks.value.length}`)
    if (tasks.value.length > 0) {
      console.log('[任务列表页面] 任务示例:', tasks.value[0])
    }
  } catch (error: any) {
    console.error('[任务列表页面] 加载失败:', error)
    ElMessage.error('加载任务列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 删除任务
const handleDeleteTask = async (taskId: number) => {
  console.log(`[任务列表页面] 用户点击删除任务: 任务ID=${taskId}`)
  
  try {
    await ElMessageBox.confirm(
      '删除任务将同步删除MySQL和图数据库中的相关数据，此操作不可恢复。确定要删除吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    console.log(`[任务列表页面] 用户确认删除: 任务ID=${taskId}`)
    deletingTaskId.value = taskId
    
    const startTime = Date.now()
    await deleteExtractionTask(taskId)
    const duration = Date.now() - startTime
    
    console.log(`[任务列表页面] 删除成功: 任务ID=${taskId}, 耗时=${duration}ms`)
    ElMessage.success('任务删除成功')
    
    // 重新加载任务列表
    console.log('[任务列表页面] 重新加载任务列表')
    await loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(`[任务列表页面] 删除失败: 任务ID=${taskId}, 错误=`, error)
      ElMessage.error('删除任务失败: ' + (error.message || '未知错误'))
    } else {
      console.log(`[任务列表页面] 用户取消删除: 任务ID=${taskId}`)
    }
  } finally {
    deletingTaskId.value = null
  }
}

// 重新生成任务
const handleRegenerateTask = async (taskId: number) => {
  console.log(`[任务列表页面] 用户点击重新生成任务: 任务ID=${taskId}`)
  
  try {
    await ElMessageBox.confirm(
      '重新生成任务将先删除现有数据，然后重新提取实体。确定要继续吗？',
      '确认重新生成',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    console.log(`[任务列表页面] 用户确认重新生成: 任务ID=${taskId}`)
    regeneratingTaskId.value = taskId
    
    const startTime = Date.now()
    const res = await regenerateExtractionTask(taskId)
    const duration = Date.now() - startTime
    
    console.log(`[任务列表页面] 重新生成成功: 旧任务ID=${taskId}, 新任务ID=${res.data.new_task_id}, 文档ID=${res.data.document_id}, 耗时=${duration}ms`)
    ElMessage.success('任务重新生成成功，新任务已启动')
    
    // 重新加载任务列表
    console.log('[任务列表页面] 重新加载任务列表')
    await loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(`[任务列表页面] 重新生成失败: 任务ID=${taskId}, 错误=`, error)
      ElMessage.error('重新生成任务失败: ' + (error.message || '未知错误'))
    } else {
      console.log(`[任务列表页面] 用户取消重新生成: 任务ID=${taskId}`)
    }
  } finally {
    regeneratingTaskId.value = null
  }
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const typeMap: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  if (!dateTime) return '-'
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(async () => {
  console.log('[任务列表页面] 页面加载')
  await loadKnowledgeBases()
})
</script>

<style scoped lang="scss">
.extraction-tasks-page {
  padding: 20px;

  :deep(.el-card) {
    background-color: rgba(6, 12, 24, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.85);

    .el-card__header {
      background-color: rgba(6, 12, 24, 0.8) !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      color: rgba(255, 255, 255, 0.9);
    }

    .el-card__body {
      background-color: rgba(6, 12, 24, 0.4) !important;
      color: rgba(255, 255, 255, 0.85);
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: rgba(255, 255, 255, 0.9);

    .header-actions {
      display: flex;
      align-items: center;
    }
  }

  .empty-state {
    padding: 40px;
    text-align: center;
    color: rgba(255, 255, 255, 0.6);
  }

  // 表格样式 - 深色主题
  :deep(.el-table) {
    background-color: rgba(6, 12, 24, 0.4) !important;
    color: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);

    // 表格头部
    .el-table__header-wrapper {
      background-color: rgba(6, 12, 24, 0.8) !important;

      th {
        background-color: rgba(6, 12, 24, 0.8) !important;
        color: rgba(255, 255, 255, 0.9) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
        font-weight: 600;

        .cell {
          color: rgba(255, 255, 255, 0.9) !important;
          font-weight: 600;
        }
      }
    }

    // 表格主体
    .el-table__body-wrapper {
      background-color: rgba(6, 12, 24, 0.4) !important;

      tr {
        background-color: rgba(6, 12, 24, 0.4) !important;
        color: rgba(255, 255, 255, 0.85);

        &:hover {
          background-color: rgba(64, 158, 255, 0.15) !important;
        }

        td {
          background-color: rgba(6, 12, 24, 0.4) !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.85);

          .cell {
            color: rgba(255, 255, 255, 0.85) !important;
          }
        }
      }

      // 斑马纹样式（stripe）
      tr.el-table__row--striped {
        background-color: rgba(255, 255, 255, 0.03) !important;

        td {
          background-color: rgba(255, 255, 255, 0.03) !important;
        }

        &:hover {
          background-color: rgba(64, 158, 255, 0.15) !important;

          td {
            background-color: rgba(64, 158, 255, 0.15) !important;
          }
        }
      }
    }

    // 边框样式
    &::before {
      background-color: rgba(255, 255, 255, 0.1);
    }
  }

  // 分页组件样式
  :deep(.el-pagination) {
    color: rgba(255, 255, 255, 0.85);

    .el-pagination__total,
    .el-pagination__jump {
      color: rgba(255, 255, 255, 0.85);
    }

    .btn-prev,
    .btn-next,
    .el-pager li {
      background-color: rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.1);

      &:hover {
        color: #409eff;
      }

      &.is-active {
        background-color: #409eff;
        color: #ffffff;
      }
    }

    .el-pagination__sizes .el-select .el-select__wrapper {
      background-color: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .el-input__wrapper {
      background-color: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: none;

      .el-input__inner {
        color: rgba(255, 255, 255, 0.85);
      }
    }
  }

  // Select 下拉框样式
  :deep(.el-select) {
    .el-select__wrapper {
      background-color: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);

      .el-select__placeholder {
        color: rgba(255, 255, 255, 0.5);
      }

      .el-select__selected-item {
        color: rgba(255, 255, 255, 0.85);
      }
    }

    .el-select__caret {
      color: rgba(255, 255, 255, 0.6);
    }
  }

  // Select 下拉菜单样式
  :deep(.el-select-dropdown) {
    background-color: rgba(26, 26, 26, 0.95) !important;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .el-select-dropdown__item {
      background-color: transparent;
      color: rgba(255, 255, 255, 0.85);

      &:hover {
        background-color: rgba(64, 158, 255, 0.15);
      }

      &.selected {
        background-color: rgba(64, 158, 255, 0.2);
        color: #409eff;
      }
    }
  }

  // Empty 组件样式
  :deep(.el-empty) {
    .el-empty__description {
      color: rgba(255, 255, 255, 0.6);
    }
  }
}
</style>
