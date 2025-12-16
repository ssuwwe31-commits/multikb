<template>
  <div class="document-versions-page" v-loading="loading">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>文档版本历史 - {{ document?.title }}</span>
          <div>
            <el-button type="primary" @click="$router.back()">返回</el-button>
          </div>
        </div>
      </template>

      <el-table :data="versions" border>
        <el-table-column prop="version_number" label="版本号" width="120" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row, $index }">
            <el-button size="small" @click="handleCompare(row)">对比</el-button>
            <el-button size="small" type="primary" @click="handleRestore(row)">恢复</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)" :disabled="$index === 0">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 版本对比对话框 -->
    <el-dialog v-model="compareVisible" title="版本对比" width="90%">
      <div class="compare-container">
        <div class="compare-left">
          <h3>{{ compareVersions.new?.version_number }}</h3>
          <pre>{{ compareVersions.new?.content || '无内容' }}</pre>
        </div>
        <div class="compare-right">
          <h3>{{ compareVersions.old?.version_number }}</h3>
          <pre>{{ compareVersions.old?.content || '无内容' }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDocumentDetail } from '@/api/modules/documents'
import { formatDateTime, formatFileSize } from '@/utils/format'

const route = useRoute()
const documentId = Number(route.params.id)

const document = ref<any>(null)
const versions = ref<any[]>([])
const loading = ref(false)
const compareVisible = ref(false)
const compareVersions = ref({
  new: null as any,
  old: null as any
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDocumentDetail(documentId)
    document.value = res.data
    versions.value = res.data.versions || []
  } catch (error) {
    ElMessage.error('加载版本历史失败')
  } finally {
    loading.value = false
  }
}

const handleCompare = (version: any) => {
  // TODO: 实现版本对比
  compareVersions.value.new = version
  compareVersions.value.old = versions.value.find(v => v.id !== version.id)
  compareVisible.value = true
}

const handleRestore = async (version: any) => {
  try {
    await ElMessageBox.confirm('确定要恢复到此版本吗？', '提示')
    // TODO: 实现版本恢复
    ElMessage.success('恢复成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('恢复失败')
    }
  }
}

const handleDelete = async (version: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该版本吗？', '提示')
    // TODO: 实现版本删除
    ElMessage.success('删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.document-versions-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .compare-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    max-height: 600px;
    overflow-y: auto;

    .compare-left,
    .compare-right {
      h3 {
        margin-bottom: 10px;
      }

      pre {
        padding: 10px;
        background: #f5f5f5;
        border-radius: 4px;
        white-space: pre-wrap;
        word-break: break-all;
      }
    }
  }
}
</style>
