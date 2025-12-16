<template>
  <el-card class="knowledge-base-card" shadow="hover" @click="handleClick">
    <template #header>
      <div class="card-header">
        <el-icon><collection /></el-icon>
        <span class="title">{{ knowledgeBase.name }}</span>
      </div>
    </template>

    <div class="card-content">
      <p class="description">{{ knowledgeBase.description }}</p>
      
      <div class="meta-info">
        <span class="category">{{ knowledgeBase.category_name }}</span>
        <el-tag :type="getStatusType(knowledgeBase.status)" size="small">
          {{ getStatusText(knowledgeBase.status) }}
        </el-tag>
      </div>

      <div class="doc-count">
        <el-icon><document /></el-icon>
        <span>{{ documentCount || 0 }} 个文档</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Collection, Document } from '@element-plus/icons-vue'
import type { KnowledgeBase } from '@/types'

const props = defineProps<{
  knowledgeBase: KnowledgeBase
  documentCount?: number
}>()

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click', props.knowledgeBase)
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    'active': 'success',
    'inactive': 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    'active': '活跃',
    'inactive': '不活跃'
  }
  return map[status] || status
}
</script>

<style lang="scss" scoped>
.knowledge-base-card {
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
      font-size: 16px;
    }
  }

  .card-content {
    .description {
      color: #666;
      margin-bottom: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }

    .meta-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      .category {
        color: #409eff;
      }
    }

    .doc-count {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #999;
      font-size: 14px;
    }
  }
}
</style>
