<template>
  <div class="knowledge-base-detail-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识库详情</span>
          <div>
            <el-button @click="handleEdit">编辑</el-button>
            <el-button type="danger" @click="handleDelete">删除</el-button>
          </div>
        </div>
      </template>

      <div v-if="detail" class="detail-content">
        <div class="tech-info-panel">
          <div class="info-item">
            <div class="info-label">
              <el-icon class="label-icon"><DocumentIcon /></el-icon>
              <span>名称</span>
            </div>
            <div class="info-value">{{ detail.name }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">
              <el-icon class="label-icon"><Folder /></el-icon>
              <span>分类</span>
            </div>
            <div class="info-value">{{ detail.category_name || '—' }}</div>
          </div>
          <div class="info-item full-width">
            <div class="info-label">
              <el-icon class="label-icon"><DocumentIcon /></el-icon>
              <span>描述</span>
            </div>
            <div class="info-value">{{ detail.description || '—' }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">
              <el-icon class="label-icon"><CircleCheck /></el-icon>
              <span>状态</span>
            </div>
            <div class="info-value">
              <el-tag :type="detail.is_active ? 'success' : 'info'" class="status-tag">
                {{ detail.is_active ? '启用' : '禁用' }}
              </el-tag>
            </div>
          </div>
          <div class="info-item">
            <div class="info-label">
              <el-icon class="label-icon"><Clock /></el-icon>
              <span>创建时间</span>
            </div>
            <div class="info-value">{{ formatDateTime(detail.created_at) }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">
              <el-icon class="label-icon"><Clock /></el-icon>
              <span>更新时间</span>
            </div>
            <div class="info-value">{{ formatDateTime(detail.updated_at) }}</div>
          </div>
        </div>

        <el-divider>文档列表</el-divider>

        <el-table :data="documents" v-loading="documentsLoading">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="file_name" label="文件名" />
          <el-table-column prop="file_type" label="类型" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button size="small" @click="viewDocument(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="docPage"
          v-model:page-size="docSize"
          :total="docTotal"
          @current-change="loadDocuments"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Document as DocumentIcon, Folder, CircleCheck, Clock } from '@element-plus/icons-vue'
import { getKnowledgeBaseDetail, deleteKnowledgeBase } from '@/api/modules/knowledge-bases'
import { getDocuments } from '@/api/modules/documents'
import { formatDateTime } from '@/utils/format'
import type { KnowledgeBase, Document } from '@/types'

const route = useRoute()
const router = useRouter()
const knowledgeBaseId = Number(route.params.id)

const detail = ref<KnowledgeBase | null>(null)
const documents = ref<Document[]>([])
const documentsLoading = ref(false)
const docPage = ref(1)
const docSize = ref(20)
const docTotal = ref(0)

const loadDetail = async () => {
  try {
    const res = await getKnowledgeBaseDetail(knowledgeBaseId)
    detail.value = res.data
  } catch (error) {
    ElMessage.error('加载详情失败')
    router.back()
  }
}

const loadDocuments = async () => {
  documentsLoading.value = true
  try {
    const res = await getDocuments({
      knowledge_base_id: knowledgeBaseId,
      page: docPage.value,
      size: docSize.value
    })
    const data = res.data || {}
    documents.value = data.list ?? data.items ?? []
    docTotal.value = data.total ?? 0
  } catch (error) {
    ElMessage.error('加载文档列表失败')
  } finally {
    documentsLoading.value = false
  }
}

const handleEdit = () => {
  router.push(`/knowledge-bases/${knowledgeBaseId}/edit`)
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要删除该知识库吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteKnowledgeBase(knowledgeBaseId)
    ElMessage.success('删除成功')
    router.push('/knowledge-bases')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const viewDocument = (doc: Document) => {
  router.push(`/documents/${doc.id}`)
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    'completed': 'success',
    'processing': 'warning',
    'failed': 'danger',
    'pending': 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    'completed': '已完成',
    'processing': '处理中',
    'failed': '失败',
    'pending': '待处理'
  }
  return map[status] || status
}

onMounted(() => {
  loadDetail()
  loadDocuments()
})
</script>

<style lang="scss" scoped>
.knowledge-base-detail-page {
  :deep(.el-card) {
    background: rgba(6, 12, 24, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.9);
    
    .el-card__header {
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      color: rgba(255, 255, 255, 0.95);
    }
    
    .el-card__body {
      color: rgba(255, 255, 255, 0.85);
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: rgba(255, 255, 255, 0.95);
  }

  .detail-content {
    .el-descriptions {
      margin-bottom: 20px;
    }
  }
  
  /* 优化表格 hover 效果，适配深色主题 */
  :deep(.el-table) {
    --el-table-row-hover-bg-color: rgba(64, 158, 255, 0.12) !important;
    background-color: transparent;
    color: rgba(255, 255, 255, 0.85);
    
    .el-table__header-wrapper {
      background-color: rgba(6, 12, 24, 0.6);
      
      th {
        background-color: rgba(6, 12, 24, 0.6) !important;
        color: rgba(255, 255, 255, 0.9) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      }
    }
    
    .el-table__body-wrapper {
      background-color: transparent;
      
      tr {
        background-color: transparent;
        color: rgba(255, 255, 255, 0.85);
        
        &:hover {
          background-color: rgba(64, 158, 255, 0.12) !important;
          
          td {
            background-color: rgba(64, 158, 255, 0.12) !important;
            color: rgba(255, 255, 255, 0.95) !important;
          }
        }
        
        td {
          background-color: transparent;
          color: rgba(255, 255, 255, 0.85);
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
      }
      
      tr.el-table__row--striped {
        background-color: rgba(255, 255, 255, 0.03);
        
        &:hover {
          background-color: rgba(64, 158, 255, 0.12) !important;
          
          td {
            background-color: rgba(64, 158, 255, 0.12) !important;
          }
        }
      }
    }
  }
  
  /* 科技感信息面板 */
  .tech-info-panel {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 24px;
    padding: 24px;
    background: linear-gradient(135deg, rgba(6, 12, 24, 0.95) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(64, 158, 255, 0.3);
    border-radius: 12px;
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
    
    .info-item {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(64, 158, 255, 0.15);
      border-radius: 8px;
      transition: all 0.3s ease;
      position: relative;
      z-index: 1;
      
      &:hover {
        background: rgba(64, 158, 255, 0.08);
        border-color: rgba(64, 158, 255, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
      }
      
      &.full-width {
        grid-column: 1 / -1;
      }
      
      .info-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.7);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
        
        .label-icon {
          font-size: 16px;
          color: #409eff;
          filter: drop-shadow(0 0 3px rgba(64, 158, 255, 0.4));
        }
      }
      
      .info-value {
        font-size: 15px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.95);
        line-height: 1.6;
        word-break: break-word;
        
        .status-tag {
          font-weight: 500;
          padding: 4px 12px;
          border-radius: 4px;
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
  
  /* 优化分页组件样式 */
  :deep(.el-pagination) {
    color: rgba(255, 255, 255, 0.85);
    margin-top: 16px;
    
    .el-pagination__total,
    .el-pagination__jump {
      color: rgba(255, 255, 255, 0.85);
    }
    
    .btn-prev,
    .btn-next {
      color: rgba(255, 255, 255, 0.85);
      
      &:hover {
        color: #409eff;
      }
      
      &.disabled {
        color: rgba(255, 255, 255, 0.3);
      }
    }
    
    .el-pager li {
      color: rgba(255, 255, 255, 0.85);
      background-color: transparent;
      
      &:hover {
        color: #409eff;
      }
      
      &.is-active {
        color: #409eff;
        background-color: rgba(64, 158, 255, 0.2);
      }
    }
    
    .el-pagination__editor {
      .el-input {
        .el-input__inner {
          background-color: rgba(255, 255, 255, 0.08) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
          color: rgba(255, 255, 255, 0.95) !important;
          font-size: 14px;
          width: 50px;
          height: 32px;
          text-align: center;
          
          &::placeholder {
            color: rgba(255, 255, 255, 0.5) !important;
          }
          
          &:focus {
            border-color: #409eff !important;
            background-color: rgba(255, 255, 255, 0.12) !important;
          }
        }
        
        .el-input__wrapper {
          background-color: rgba(255, 255, 255, 0.08) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
          box-shadow: none !important;
          
          &.is-focus {
            border-color: #409eff !important;
            box-shadow: 0 0 0 1px #409eff inset !important;
          }
        }
      }
    }
  }
  
  /* 优化按钮样式 */
  :deep(.el-button) {
    &:not(.el-button--primary):not(.el-button--danger) {
      color: rgba(255, 255, 255, 0.85);
      border-color: rgba(255, 255, 255, 0.3);
      background-color: rgba(255, 255, 255, 0.05);
      
      &:hover {
        color: #409eff;
        border-color: #409eff;
        background-color: rgba(64, 158, 255, 0.1);
      }
    }
  }
  
  /* 优化分割线样式 */
  :deep(.el-divider) {
    border-color: rgba(255, 255, 255, 0.1);
    
    .el-divider__text {
      background-color: rgba(6, 12, 24, 0.9);
      color: rgba(255, 255, 255, 0.85);
      font-size: 16px;
      font-weight: 600;
    }
  }
}
</style>
