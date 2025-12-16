<template>
  <div class="qa-history-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>问答历史</span>
          <div>
            <el-select v-model="selectedSessionId" placeholder="选择会话" clearable style="width: 200px;">
              <el-option
                v-for="session in sessions"
                :key="session.id"
                :label="session.knowledge_base_name"
                :value="session.id"
              />
            </el-select>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="历史记录" name="records">
          <BaseTable
            :data="historyRecords"
            :loading="loading"
            @row-click="viewRecord"
          >
            <el-table-column prop="question" label="问题" show-overflow-tooltip />
            <el-table-column prop="answer" label="回答" show-overflow-tooltip />
            <el-table-column prop="session_name" label="会话" width="150" />
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="viewRecord(row)">查看</el-button>
                <el-button size="small" type="danger" @click="deleteRecord(row)">删除</el-button>
              </template>
            </el-table-column>
          </BaseTable>
        </el-tab-pane>

        <el-tab-pane label="会话列表" name="sessions">
          <BaseTable :data="sessions" :loading="loading">
            <el-table-column prop="knowledge_base_name" label="知识库" />
            <el-table-column prop="question_count" label="问题数" width="100" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="openSession(row)">打开</el-button>
                <el-button size="small" type="danger" @click="deleteSession(row)">删除</el-button>
              </template>
            </el-table-column>
          </BaseTable>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useQAStore } from '@/stores/modules/qa'
import { getQAHistory, deleteQAHistory } from '@/api/modules/qa'
import { formatDateTime } from '@/utils/format'
import BaseTable from '@/components/common/BaseTable.vue'

const router = useRouter()
const qaStore = useQAStore()

const historyRecords = ref<any[]>([])
const sessions = ref<any[]>([])
const activeTab = ref('records')
const selectedSessionId = ref<number | null>(null)
const loading = ref(false)

const loadData = async () => {
  loading.value = true
  try {
    const res = await getQAHistory({
      page: 1,
      size: 100,
      session_id: selectedSessionId.value || undefined
    })
    historyRecords.value = res.data.results || []
    
    await qaStore.loadSessions()
    sessions.value = qaStore.sessions
  } catch (error) {
    ElMessage.error('加载历史记录失败')
  } finally {
    loading.value = false
  }
}

const viewRecord = (record: any) => {
  // TODO: 显示详细记录
  ElMessage.info('查看详情功能待实现')
}

const deleteRecord = async (record: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该记录吗？', '提示')
    await deleteQAHistory(record.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const openSession = (session: any) => {
  router.push(`/qa/chat?session_id=${session.id}`)
}

const deleteSession = async (session: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该会话吗？', '提示')
    await qaStore.deleteSession(session.id)
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
.qa-history-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
