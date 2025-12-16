<template>
  <div class="structured-preview">
    <div v-loading="loading">
      <!-- JSON预览 -->
      <div v-if="previewData?.type === 'json'">
        <vue-json-pretty
          v-if="previewData.content"
          :data="previewData.content"
          :show-length="true"
          :deep="5"
          :show-line="true"
        />
        <el-alert v-else type="info" :closable="false">
          预览数据生成中，请稍后刷新
        </el-alert>
      </div>

      <!-- XML预览 -->
      <div v-else-if="previewData?.type === 'xml'">
        <div v-if="previewData.content" class="xml-preview">
          <vue-json-pretty
            :data="previewData.content"
            :show-length="true"
            :deep="5"
            :show-line="true"
          />
        </div>
        <el-alert v-else type="info" :closable="false">
          预览数据生成中，请稍后刷新
        </el-alert>
      </div>

      <!-- CSV预览 -->
      <div v-else-if="previewData?.type === 'csv'">
        <el-table
          v-if="previewData.content && Array.isArray(previewData.content)"
          :data="previewData.content"
          stripe
          border
          max-height="600"
        >
          <el-table-column
            v-for="(header, index) in csvHeaders"
            :key="index"
            :prop="header"
            :label="header"
            show-overflow-tooltip
          />
        </el-table>
        <el-alert v-else type="info" :closable="false">
          预览数据生成中，请稍后刷新
        </el-alert>
      </div>

      <el-alert v-else type="warning" :closable="false">
        该文档不支持结构化预览
      </el-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getStructuredPreview } from '@/api/modules/documents'
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

// 在 Vue 3 script setup 中，导入的组件会自动注册，无需显式注册

const props = defineProps<{
  documentId: number
}>()

const loading = ref(false)
const previewData = ref<any>(null)

const csvHeaders = computed(() => {
  if (previewData.value?.type === 'csv' && Array.isArray(previewData.value.content) && previewData.value.content.length > 0) {
    return Object.keys(previewData.value.content[0])
  }
  return []
})

const loadPreview = async () => {
  loading.value = true
  try {
    const res = await getStructuredPreview(props.documentId)
    previewData.value = res.data || res
  } catch (error) {
    console.error('加载结构化预览失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPreview()
})
</script>

<style scoped>
.structured-preview {
  padding: 16px;
}

.xml-preview {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}
</style>
