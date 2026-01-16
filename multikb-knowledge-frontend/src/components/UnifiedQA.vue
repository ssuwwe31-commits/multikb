<template>
  <div class="unified-qa">
    <el-card class="qa-card">
      <template #header>
        <div class="card-header">
          <span>💬 智能问答</span>
          <el-tag size="small" type="success">文档 + 代码</el-tag>
        </div>
      </template>

      <!-- 问题输入 -->
      <el-input
        v-model="question"
        type="textarea"
        :rows="3"
        placeholder="请输入你的问题..."
        class="question-input"
      />

      <!-- 选项 -->
      <div class="qa-options">
        <el-checkbox v-model="includeCode" label="包含代码上下文" />
        <el-input-number
          v-model="maxSources"
          :min="1"
          :max="10"
          size="small"
          controls-position="right"
        />
        <span class="option-label">最大来源数</span>
      </div>

      <!-- 提交按钮 -->
      <el-button
        type="primary"
        @click="handleAsk"
        :loading="loading"
        :disabled="!question.trim()"
        class="ask-button"
        size="large"
      >
        <el-icon><ChatDotRound /></el-icon>
        提问
      </el-button>

      <!-- 答案显示 -->
      <div v-if="answer" class="answer-section">
        <el-divider>答案</el-divider>
        
        <div class="answer-content">
          {{ answer.answer }}
        </div>

        <!-- 来源列表 -->
        <div v-if="answer.sources && answer.sources.length > 0" class="sources-section">
          <el-divider>参考来源（{{ answer.sources.length }}）</el-divider>
          
          <div class="sources-list">
            <div
              v-for="(source, index) in answer.sources"
              :key="`source-${index}`"
              class="source-item"
            >
              <!-- 文档来源 -->
              <div v-if="source.type === 'document'" class="source-document">
                <el-icon color="#409EFF"><Document /></el-icon>
                <span>{{ source.title }}</span>
                <el-tag size="small" type="info">文档</el-tag>
              </div>

              <!-- 代码文件来源 -->
              <div v-if="source.type === 'code_file'" class="source-code-file">
                <el-icon color="#67C23A"><Folder /></el-icon>
                <span>{{ source.file_path }}</span>
                <el-tag size="small" type="success">{{ source.language }}</el-tag>
              </div>

              <!-- 代码符号来源 -->
              <div v-if="source.type === 'code_symbol'" class="source-code-symbol">
                <el-icon color="#E6A23C"><Promotion /></el-icon>
                <span>{{ source.symbol_name }}</span>
                <el-tag size="small" type="warning">{{ source.symbol_type }}</el-tag>
              </div>

              <span class="source-score">{{ (source.score * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-else-if="asked && !loading"
        description="暂无答案"
        :image-size="80"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ChatDotRound, Document, Folder, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as unifiedQAApi from '@/api/modules/unified-qa'

// =============================================
// Props
// =============================================

const props = defineProps<{
  knowledgeBaseId?: number
}>()

// =============================================
// 状态
// =============================================

const question = ref('')
const includeCode = ref(true)
const maxSources = ref(5)
const loading = ref(false)
const asked = ref(false)
const answer = ref<any>(null)

// =============================================
// 方法
// =============================================

const handleAsk = async () => {
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  loading.value = true
  asked.value = true

  try {
    const scope = includeCode.value ? ['documents', 'code'] : ['documents']

    const response = await unifiedQAApi.unifiedQA({
      question: question.value,
      knowledge_base_id: props.knowledgeBaseId,
      search_scope: scope as any,
      max_context_items: maxSources.value,
      include_code_context: includeCode.value
    })

    if (response.code === 200) {
      answer.value = response.data
      ElMessage.success('获取答案成功')
    } else {
      ElMessage.error(response.message || '问答失败')
      answer.value = null
    }
  } catch (error: any) {
    console.error('问答失败:', error)
    ElMessage.error('问答失败: ' + (error.message || '未知错误'))
    answer.value = null
  } finally {
    loading.value = false
  }
}

// 清空
const reset = () => {
  question.value = ''
  answer.value = null
  asked.value = false
}

// 暴露方法
defineExpose({
  reset
})
</script>

<style scoped lang="scss">
.unified-qa {
  .qa-card {
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }

    .question-input {
      margin-bottom: 16px;
    }

    .qa-options {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;

      .option-label {
        color: #606266;
        font-size: 14px;
      }
    }

    .ask-button {
      width: 100%;
      margin-bottom: 16px;
    }

    .answer-section {
      margin-top: 16px;

      .answer-content {
        padding: 16px;
        background: #f5f7fa;
        border-radius: 4px;
        line-height: 1.8;
        color: #303133;
        white-space: pre-wrap;
      }

      .sources-section {
        margin-top: 16px;

        .sources-list {
          .source-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            border: 1px solid #ebeef5;
            border-radius: 4px;
            margin-bottom: 8px;
            transition: all 0.3s;

            &:hover {
              background: #f5f7fa;
              border-color: #409EFF;
            }

            > span {
              flex: 1;
              font-size: 13px;
            }

            .source-score {
              color: #909399;
              font-size: 12px;
              flex: none;
            }
          }
        }
      }
    }
  }
}
</style>
