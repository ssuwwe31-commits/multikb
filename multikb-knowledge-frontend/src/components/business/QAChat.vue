<template>
  <div class="qa-chat">
    <!-- 查询方式选择 -->
    <div class="query-config">
      <el-select v-model="selectedQueryMethod" placeholder="选择查询方式" size="small" style="width: 150px">
        <el-option label="向量检索" value="vector" />
        <el-option label="关键词检索" value="keyword" />
        <el-option label="混合检索" value="hybrid" />
        <el-option label="精确匹配" value="exact" />
        <el-option label="模糊搜索" value="fuzzy" />
        <el-option label="多模态检索" value="multimodal" />
      </el-select>
      <el-select v-model="selectedInputType" placeholder="输入类型" size="small" style="width: 120px">
        <el-option label="文本" value="text" />
        <el-option label="图片" value="image" />
        <el-option label="图文混合" value="multimodal" />
      </el-select>
    </div>

    <div class="chat-messages" ref="messagesRef">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message"
        :class="{ 'user-message': message.type === 'user', 'assistant-message': message.type === 'assistant' }">
        <div class="message-content" v-html="formatMessage(message.content)"></div>
        
        <!-- 引用溯源 -->
        <div v-if="message.citations && message.citations.length > 0" class="citations">
          <el-divider content-position="left">引用来源</el-divider>
          <div v-for="(citation, idx) in message.citations" :key="idx" class="citation-item">
            <el-link type="primary" @click="viewCitation(citation)">{{ citation.source }}</el-link>
            <span class="relevance">相关度: {{ citation.score }}</span>
          </div>
        </div>

        <!-- 降级策略提示 -->
        <div v-if="message.fallback_info" class="fallback-info">
          <el-alert :type="getFallbackType(message.fallback_info.level)" size="small">
            {{ getFallbackMessage(message.fallback_info.level) }}
          </el-alert>
        </div>

        <div class="message-time">{{ formatDateTime(message.created_at) }}</div>
      </div>
    </div>

    <div class="chat-input-area">
      <!-- 图片上传预览 -->
      <div v-if="selectedImages.length > 0" class="image-preview">
        <div v-for="(img, idx) in selectedImages" :key="idx" class="preview-item">
          <img :src="img.url" alt="preview" />
          <el-icon class="close-icon" @click="removeImage(idx)"><Close /></el-icon>
        </div>
      </div>

      <el-input
        v-model="inputText"
        type="textarea"
        :rows="3"
        placeholder="请输入问题..."
        @keydown.ctrl.enter="handleSend"
        @keydown.meta.enter="handleSend"
      />
      
      <div class="input-actions">
        <el-upload
          :show-file-list="false"
          :before-upload="handleImageUpload"
          accept="image/*"
          style="display: inline-block; margin-right: 10px">
          <el-button size="small">
            <el-icon><picture /></el-icon>
            上传图片
          </el-button>
        </el-upload>

        <el-switch v-model="enableStreaming" active-text="流式输出" size="small" />

        <el-button type="primary" @click="handleSend" :loading="sending" :disabled="!canSend">
          发送
        </el-button>
      </div>
    </div>

    <!-- 引用查看器 -->
    <CitationViewer
      v-model="showCitationViewer"
      :citation="selectedCitation"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, Close } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import { useQAStore, type QueryMethod, type InputType } from '@/stores/modules/qa'
import { askQuestion, getStreamURL } from '@/api/modules/qa'
import CitationViewer from './CitationViewer.vue'
import { WebSocketClient } from '@/utils/websocketClient'

const props = defineProps<{
  sessionId: string
}>()

const emit = defineEmits(['send-message'])

const qaStore = useQAStore()
const messages = ref<any[]>([])
const inputText = ref('')
const sending = ref(false)
const messagesRef = ref<HTMLElement>()
const selectedQueryMethod = ref<QueryMethod>('hybrid')
const selectedInputType = ref<InputType>('text')
const selectedImages = ref<Array<{ file: File; url: string }>>([])
const enableStreaming = ref(true)
const wsClient = ref<WebSocketClient | null>(null)

// 引用查看器
const showCitationViewer = ref(false)
const selectedCitation = ref<any>(null)

const canSend = computed(() => inputText.value.trim().length > 0 || selectedImages.value.length > 0)

// 发送消息
const handleSend = async () => {
  if (!canSend.value || sending.value) return

  // 添加用户消息
  const userMessage = {
    id: Date.now(),
    type: 'user',
    content: inputText.value || '[图片]',
    images: selectedImages.value.map(img => img.file),
    created_at: new Date().toISOString()
  }
  messages.value.push(userMessage)
  scrollToBottom()

  // 发送到服务器
  sending.value = true
  try {
    if (enableStreaming.value) {
      await handleStreamAnswer(userMessage)
    } else {
      await handleNormalAnswer(userMessage)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '发送失败')
  } finally {
    inputText.value = ''
    selectedImages.value = []
    sending.value = false
  }
}

// 流式回答
const handleStreamAnswer = async (message: any) => {
  if (!wsClient.value || !wsClient.value.isConnected()) {
    initWebSocket()
  }
  
  // 等待连接
  await new Promise(resolve => setTimeout(resolve, 100))
  
  // 发送问题到WebSocket
  const questionData = {
    text_content: message.content,
    image_files: message.images,
    input_type: selectedInputType.value,
    search_type: selectedQueryMethod.value,
    similarity_threshold: 0.7,
    max_sources: 5
  }
  
  wsClient.value?.send(questionData)

  // 添加占位符回答
  const answerId = Date.now() + 1
  messages.value.push({
    id: answerId,
    type: 'assistant',
    content: '',
    created_at: new Date().toISOString()
  })
}

// 普通回答
const handleNormalAnswer = async (message: any) => {
  const formData = new FormData()
  if (message.images && message.images.length > 0) {
    message.images.forEach((file: File) => {
      formData.append('image_file', file)
    })
  }
  if (inputText.value) {
    formData.append('text_content', message.content)
  }
  formData.append('input_type', selectedInputType.value)
  formData.append('search_type', selectedQueryMethod.value)

  const res = await askQuestion(props.sessionId, {
    text_content: message.content || undefined,
    image_file: message.images?.[0],
    input_type: selectedInputType.value,
    search_type: selectedQueryMethod.value,
    similarity_threshold: 0.7,
    max_sources: 5
  })

  // 添加助手回答
  messages.value.push({
    id: Date.now(),
    type: 'assistant',
    content: res.data.answer,
    citations: res.data.citations,
    fallback_info: res.data.fallback_info,
    created_at: new Date().toISOString()
  })
  scrollToBottom()
}

// 初始化WebSocket（使用新的WebSocketClient）
const initWebSocket = () => {
  const wsUrl = getStreamURL(props.sessionId)
  wsClient.value = new WebSocketClient(wsUrl)

  // 订阅消息
  wsClient.value.subscribe('chunk', (data: any) => {
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage && lastMessage.type === 'assistant') {
      lastMessage.content += data.content
    }
    scrollToBottom()
  })

  wsClient.value.subscribe('done', (data: any) => {
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage && lastMessage.type === 'assistant') {
      lastMessage.citations = data.citations
      lastMessage.fallback_info = data.fallback_info
    }
    sending.value = false
  })

  // 连接回调
  wsClient.value.onConnect(() => {
    console.log('WebSocket已连接')
  })

  wsClient.value.onError((error: Error) => {
    console.error('WebSocket错误:', error)
    ElMessage.error('连接失败，切换到普通模式')
    enableStreaming.value = false
  })

  wsClient.value.onDisconnect(() => {
    console.log('WebSocket已断开')
  })

  // 连接
  wsClient.value.connect()
}

// 图片上传处理
const handleImageUpload = (file: File) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    selectedImages.value.push({
      file,
      url: e.target?.result as string
    })
  }
  reader.readAsDataURL(file)
  return false // 阻止默认上传
}

// 移除图片
const removeImage = (index: number) => {
  selectedImages.value.splice(index, 1)
}

// 查看引用来源
const viewCitation = (citation: any) => {
  selectedCitation.value = citation
  showCitationViewer.value = true
}

// 获取降级策略类型
const getFallbackType = (level: string) => {
  const types: Record<string, any> = {
    knowledge_base: 'success',
    llm: 'warning',
    no_info: 'error'
  }
  return types[level] || 'info'
}

// 获取降级策略消息
const getFallbackMessage = (level: string) => {
  const messages: Record<string, string> = {
    knowledge_base: '基于知识库回答',
    llm: '基于大模型回答',
    no_info: '无可用信息'
  }
  return messages[level] || ''
}

const formatMessage = (content: string) => {
  return content.replace(/\n/g, '<br>')
}

const addMessage = (message: any) => {
  messages.value.push(message)
  scrollToBottom()
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

watch(messages, scrollToBottom, { deep: true })

// 生命周期
onMounted(() => {
  // 初始化WebSocket
  if (enableStreaming.value) {
    initWebSocket()
  }
})

onUnmounted(() => {
  // 关闭WebSocket
  if (wsClient.value) {
    wsClient.value.disconnect()
    wsClient.value = null
  }
})

defineExpose({
  addMessage,
  messages
})
</script>

<style lang="scss" scoped>
.qa-chat {
  height: 100%;
  display: flex;
  flex-direction: column;

  .query-config {
    padding: 10px 20px;
    background-color: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    gap: 10px;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    margin-bottom: 20px;

    .message {
      margin-bottom: 20px;
      max-width: 70%;

      &.user-message {
        margin-left: auto;
        text-align: right;

        .message-content {
          background-color: #409eff;
          color: #fff;
          display: inline-block;
          padding: 12px 16px;
          border-radius: 12px;
          word-wrap: break-word;
        }
      }

      &.assistant-message {
        .message-content {
          background-color: #f5f5f5;
          display: inline-block;
          padding: 12px 16px;
          border-radius: 12px;
          word-wrap: break-word;
        }

        .citations {
          margin-top: 10px;
          padding: 10px;
          background-color: #f9f9f9;
          border-radius: 8px;

          .citation-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;

            .relevance {
              font-size: 12px;
              color: #666;
            }
          }
        }

        .fallback-info {
          margin-top: 10px;
        }
      }

      .message-time {
        font-size: 12px;
        color: #999;
        margin-top: 5px;
      }
    }
  }

  .chat-input-area {
    padding: 10px 20px;
    border-top: 1px solid #e0e0e0;

    .image-preview {
      display: flex;
      gap: 10px;
      margin-bottom: 10px;

      .preview-item {
        position: relative;
        width: 80px;
        height: 80px;
        border: 1px solid #ddd;
        border-radius: 4px;
        overflow: hidden;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .close-icon {
          position: absolute;
          top: 2px;
          right: 2px;
          cursor: pointer;
          background-color: rgba(0, 0, 0, 0.5);
          color: white;
          border-radius: 50%;
          padding: 2px;
        }
      }
    }

    .input-actions {
      margin-top: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
</style>
