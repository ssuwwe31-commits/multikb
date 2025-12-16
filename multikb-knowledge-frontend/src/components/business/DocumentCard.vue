<template>
  <el-card class="document-card" shadow="hover" @click="handleClick">
    <template #header>
      <div class="card-header">
        <el-icon><document /></el-icon>
        <span class="title">{{ document.title || document.file_name }}</span>
      </div>
    </template>

    <div class="card-content">
      <div class="file-info">
        <el-tag size="small">{{ document.file_type }}</el-tag>
        <span class="file-size">{{ formatFileSize(document.file_size) }}</span>
      </div>

      <div class="status-info">
        <el-tag :type="getStatusType(document.status)" size="small">
          {{ getStatusText(document.status) }}
        </el-tag>
        <span class="update-time">{{ formatDateTime(document.updated_at) }}</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Document } from '@element-plus/icons-vue'
import { formatFileSize, formatDateTime } from '@/utils/format'
import type { Document as DocumentType } from '@/types'

const props = defineProps<{
  document: DocumentType
}>()

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click', props.document)
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
</script>

<style lang="scss" scoped>
.document-card {
  cursor: pointer;
  transition: transform 0.3s;

  &:hover {
    transform: translateY(-4px);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;

    .title {
      font-weight: 500;
      font-size: 14px;
    }
  }

  .card-content {
    .file-info {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;

      .file-size {
        color: #999;
        font-size: 12px;
      }
    }

    .status-info {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .update-time {
        color: #999;
        font-size: 12px;
      }
    }
  }
}
</style>
