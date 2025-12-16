<template>
  <el-dialog v-model="visible" title="引用来源详情" width="800px">
    <div class="citation-viewer" v-if="citation">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="来源文档">{{ citation.source || '未知来源' }}</el-descriptions-item>
        <el-descriptions-item label="相关度">
          <el-tag :type="getScoreType(citation.score)">
            {{ (citation.score * 100).toFixed(1) }}%
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="文档ID" :span="2">
          {{ citation.document_id || '无' }}
        </el-descriptions-item>
        <el-descriptions-item label="块ID" :span="2">
          {{ citation.chunk_id || '无' }}
        </el-descriptions-item>
        <el-descriptions-item label="块内容" :span="2">
          <div class="chunk-content">{{ citation.content || '无内容' }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">
          {{ citation.created_at ? formatDateTime(citation.created_at) : '未知' }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="actions">
        <el-button 
          type="primary" 
          @click="viewDocument"
          :disabled="!citation.document_id"
        >
          查看文档
        </el-button>
        <el-button 
          type="primary" 
          @click="viewChunk"
          :disabled="!citation.document_id || !citation.chunk_id"
        >
          查看块
        </el-button>
        <el-button @click="copyCitation">复制引用</el-button>
      </div>
    </div>
    <div v-else class="empty-citation">
      <el-empty description="无引用信息" />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/format'

const router = useRouter()

const props = defineProps<{
  modelValue: boolean
  citation: any
}>()

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 获取相关度标签类型
const getScoreType = (score: number) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'danger'
}

// 查看文档
const viewDocument = () => {
  if (!props.citation?.document_id) {
    ElMessage.warning('文档ID不存在')
    return
  }
  router.push(`/documents/${props.citation.document_id}`)
  visible.value = false
}

// 查看块
const viewChunk = () => {
  if (!props.citation?.document_id) {
    ElMessage.warning('文档ID不存在')
    return
  }
  if (!props.citation?.chunk_id) {
    ElMessage.warning('块ID不存在')
    return
  }
  router.push(`/documents/${props.citation.document_id}/chunks/${props.citation.chunk_id}`)
  visible.value = false
}

// 复制引用
const copyCitation = async () => {
  if (!props.citation) {
    ElMessage.warning('无引用信息')
    return
  }
  
  const citationText = `来源: ${props.citation.source}\n相关度: ${(props.citation.score * 100).toFixed(1)}%\n内容: ${props.citation.content}`
  
  try {
    await navigator.clipboard.writeText(citationText)
    ElMessage.success('引用已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}
</script>

<style lang="scss" scoped>
.citation-viewer {
  .chunk-content {
    max-height: 200px;
    overflow-y: auto;
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 4px;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 14px;
    line-height: 1.6;
  }

  .actions {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}

.empty-citation {
  padding: 40px 0;
  text-align: center;
}
</style>
