<template>
  <div class="qa-chat-page">
    <div class="chat-layout">
      <!-- 侧边栏 -->
      <div class="chat-sidebar">
        <el-card>
          <template #header>
            <span>会话列表</span>
          </template>

          <div class="session-list">
            <div
              v-for="session in sessions"
              :key="session.id"
              class="session-item"
              :class="{ active: currentSession?.id === session.id }"
              @click="selectSession(session)"
            >
              <div class="session-title">{{ session.knowledge_base_name }}</div>
              <div class="session-time">{{ formatDateTime(session.updated_at) }}</div>
            </div>

            <el-button type="primary" @click="handleNewSession" :disabled="!knowledgeBases.length">
              <el-icon><Plus /></el-icon>
              新建会话
            </el-button>
          </div>
        </el-card>

        <!-- 知识库选择 -->
        <el-card style="margin-top: 20px;">
          <template #header>
            <span>知识库</span>
          </template>
          <el-select
            v-model="selectedKnowledgeBaseId"
            placeholder="请选择知识库"
            @change="handleKnowledgeBaseChange"
          >
            <el-option
              v-for="kb in knowledgeBases"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
          <el-alert
            v-if="!selectedKnowledgeBaseId"
            title="请先选择知识库才能创建会话"
            type="warning"
            :closable="false"
            style="margin-top: 10px"
          />
        </el-card>
      </div>

      <!-- 主聊天区域 -->
      <div class="chat-main">
        <QAChat
          v-if="currentSession"
          :session-id="currentSession.id"
          ref="chatRef"
          @send-message="handleSendMessage"
        />

        <BaseEmpty
          v-else
          description="请选择或创建会话"
          :show-action="true"
          action-text="新建会话"
          @action="handleNewSession"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useQAStore } from '@/stores/modules/qa'
import { useKnowledgeBasesStore } from '@/stores/modules/knowledge-bases'
import QAChat from '@/components/business/QAChat.vue'
import BaseEmpty from '@/components/common/BaseEmpty.vue'
import { formatDateTime } from '@/utils/format'

const qaStore = useQAStore()
const knowledgeBasesStore = useKnowledgeBasesStore()

const chatRef = ref()
const sessions = ref<any[]>([])
const currentSession = ref<any>(null)
const selectedKnowledgeBaseId = ref<number | null>(null)
const knowledgeBases = ref<any[]>([])

const loadData = async () => {
  await qaStore.loadSessions()
  await knowledgeBasesStore.loadKnowledgeBases()
  sessions.value = qaStore.sessions
  knowledgeBases.value = knowledgeBasesStore.knowledgeBases
}

const handleNewSession = async () => {
  if (!selectedKnowledgeBaseId.value) {
    ElMessage.warning('请先选择知识库')
    return
  }

  try {
    const session = await qaStore.createSession(selectedKnowledgeBaseId.value)
    currentSession.value = session
    selectedKnowledgeBaseId.value = session.knowledge_base_id
  } catch (error) {
    ElMessage.error('创建会话失败')
  }
}

const selectSession = async (session: any) => {
  qaStore.selectSession(session)
  currentSession.value = session
}

const handleKnowledgeBaseChange = (kbId: number) => {
  selectedKnowledgeBaseId.value = kbId
}

const handleSendMessage = async (message: string) => {
  if (!currentSession.value) {
    ElMessage.warning('请先选择会话')
    return
  }

  try {
    const { askQuestion } = await import('@/api/modules/qa')
    const sessionId = currentSession.value.session_id || currentSession.value.id
    
    const res = await askQuestion(sessionId, {
      text_content: message,
      input_type: 'text',
      search_type: 'hybrid'
    })

    const response = {
      id: Date.now(),
      type: 'assistant',
      content: res.data.answer_content || res.data.answer || '暂无回答',
      created_at: new Date().toISOString(),
      source_info: res.data.source_info,
      processing_info: res.data.processing_info
    }

    // 添加到消息列表
    if (qaStore.addMessage) {
      qaStore.addMessage(response)
    }
    
    // 如果chatRef有addMessage方法，也可以调用
    if (chatRef.value?.addMessage) {
      chatRef.value.addMessage(response)
    }
  } catch (error: any) {
    console.error('发送消息失败:', error)
    ElMessage.error(error?.response?.data?.detail || '发送消息失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.qa-chat-page {
  height: 100%;
  
  .chat-layout {
    display: flex;
    height: 100%;
    gap: 20px;

    .chat-sidebar {
      width: 300px;
      height: 100%;
      overflow-y: auto;

      .session-list {
        .session-item {
          padding: 12px;
          border-radius: 4px;
          cursor: pointer;
          margin-bottom: 8px;
          transition: background-color 0.2s;

          &:hover {
            background-color: #f5f5f5;
          }

          &.active {
            background-color: #e6f7ff;
          }

          .session-title {
            font-weight: 500;
            margin-bottom: 4px;
          }

          .session-time {
            font-size: 12px;
            color: #909399;
          }
        }
      }
    }

    .chat-main {
      flex: 1;
      height: 100%;
    }
  }
}
</style>
