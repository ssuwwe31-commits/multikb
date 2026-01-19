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
        
        <div 
          class="answer-content markdown-body"
          v-html="renderedAnswer"
          ref="answerContentRef"
        ></div>

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
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { ChatDotRound, Document, Folder, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as unifiedQAApi from '@/api/modules/unified-qa'
import { marked } from 'marked'

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
const answerContentRef = ref<HTMLElement>()

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

// =============================================
// 计算属性
// =============================================

// 渲染答案内容（Markdown + Mermaid）
const renderedAnswer = computed(() => {
  if (!answer.value?.answer) return ''
  
  let content = answer.value.answer
  
  // 使用 marked 渲染 Markdown
  try {
    content = marked.parse(content) as string
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    // 降级处理：简单转义 HTML
    content = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
  
  return content
})

// =============================================
// 方法
// =============================================

// 渲染 Mermaid 图表
const renderMermaidDiagrams = async () => {
  if (!answerContentRef.value) return
  
  // 动态导入 Mermaid
  let mermaidModule: any = null
  try {
    mermaidModule = await import('mermaid')
  } catch (error) {
    console.warn('Mermaid 未安装，流程图渲染功能将不可用')
    return
  }
  
  if (!mermaidModule) return
  
  const mermaid = mermaidModule.default
  mermaid.initialize({ 
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      curve: 'basis'
    }
  })
  
  // 查找所有 Mermaid 代码块（marked 渲染后的结构）
  // marked 会将 ```mermaid 代码块渲染为 <pre><code class="language-mermaid">
  const mermaidBlocks = answerContentRef.value.querySelectorAll('pre code.language-mermaid, pre code.lang-mermaid')
  
  // 如果没有找到，尝试查找包含 mermaid 关键字的代码块
  if (mermaidBlocks.length === 0) {
    const allCodeBlocks = answerContentRef.value.querySelectorAll('pre code')
    for (const block of allCodeBlocks) {
      const text = block.textContent || ''
      if (text.includes('graph') || text.includes('flowchart') || text.includes('sequenceDiagram')) {
        // 检查是否包含 Mermaid 语法
        if (text.match(/^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|gitgraph|journey|requirement)/m)) {
          mermaidBlocks.push(block as HTMLElement)
        }
      }
    }
  }
  
  for (let i = 0; i < mermaidBlocks.length; i++) {
    const codeBlock = mermaidBlocks[i] as HTMLElement
    const mermaidCode = codeBlock.textContent || ''
    
    if (!mermaidCode.trim()) continue
    
    try {
      // 提取 Mermaid 代码（移除可能的 ```mermaid 标记）
      let code = mermaidCode.trim()
      code = code.replace(/^```mermaid\n?/i, '').replace(/```\s*$/g, '').trim()
      
      // 修复常见的 Mermaid 语法错误
      code = fixMermaidCode(code)
      
      // 创建容器
      const container = document.createElement('div')
      container.className = 'mermaid-diagram-container'
      container.style.cssText = 'margin: 16px 0; padding: 16px; background: #fff; border-radius: 4px; border: 1px solid #e4e7ed; overflow-x: auto;'
      
      // 渲染 Mermaid
      const id = `mermaid-qa-${Date.now()}-${i}`
      const { svg } = await mermaid.render(id, code)
      
      container.innerHTML = svg
      
      // 替换代码块
      const preElement = codeBlock.parentElement
      if (preElement) {
        preElement.replaceWith(container)
      }
    } catch (error: any) {
      console.error('Mermaid 渲染失败:', error)
      // 保留原始代码块，但添加错误提示
      const preElement = codeBlock.parentElement as HTMLElement
      if (preElement) {
        preElement.style.cssText = 'padding: 12px; background: #fef0f0; border: 1px solid #fde2e2; border-radius: 4px; color: #f56c6c;'
        preElement.innerHTML = `<div style="font-weight: 600; margin-bottom: 8px;">⚠️ 流程图渲染失败</div><pre style="margin: 0; white-space: pre-wrap; font-size: 12px;">${codeBlock.textContent}</pre>`
      }
    }
  }
}

// 修复 Mermaid 代码语法错误
const fixMermaidCode = (code: string): string => {
  if (!code) return code
  
  const lines = code.split('\n')
  const fixedLines: string[] = []
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim()
    if (!line) continue
    
    // 跳过注释行
    if (line.startsWith('#') || line.startsWith('//')) {
      continue
    }
    
    // 修复不完整的箭头
    if (line.includes('->') && !line.includes('-->')) {
      if (line.endsWith('->') || line.endsWith('-->')) {
        continue
      }
      line = line.replace(/ -> /g, ' --> ').replace(/->/g, ' --> ')
    }
    
    fixedLines.push(line)
  }
  
  let fixedCode = fixedLines.join('\n')
  
  // 确保有图表类型声明
  if (!fixedCode.match(/^(graph|sequenceDiagram|flowchart|classDiagram|stateDiagram|erDiagram|gantt|pie|gitgraph|journey|requirement)/)) {
    fixedCode = 'graph TD\n' + fixedCode
  }
  
  return fixedCode
}

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
      
      // 等待 DOM 更新后渲染 Mermaid
      await nextTick()
      setTimeout(() => {
        renderMermaidDiagrams()
      }, 100)
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

// 监听答案变化，重新渲染 Mermaid
watch(() => answer.value?.answer, async () => {
  if (answer.value?.answer) {
    await nextTick()
    setTimeout(() => {
      renderMermaidDiagrams()
    }, 100)
  }
}, { deep: true })

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
        
        // Markdown 样式
        :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
          margin-top: 16px;
          margin-bottom: 8px;
          font-weight: 600;
          line-height: 1.4;
        }
        
        :deep(h1) { font-size: 24px; }
        :deep(h2) { font-size: 20px; }
        :deep(h3) { font-size: 18px; }
        :deep(h4) { font-size: 16px; }
        
        :deep(p) {
          margin: 8px 0;
        }
        
        :deep(ul), :deep(ol) {
          margin: 8px 0;
          padding-left: 24px;
        }
        
        :deep(li) {
          margin: 4px 0;
        }
        
        :deep(code) {
          padding: 2px 6px;
          background: #f1f2f3;
          border-radius: 3px;
          font-family: 'Courier New', monospace;
          font-size: 0.9em;
        }
        
        :deep(pre) {
          margin: 12px 0;
          padding: 12px;
          background: #282c34;
          border-radius: 4px;
          overflow-x: auto;
          
          code {
            padding: 0;
            background: transparent;
            color: #abb2bf;
          }
        }
        
        :deep(blockquote) {
          margin: 12px 0;
          padding: 8px 16px;
          border-left: 4px solid #409EFF;
          background: #ecf5ff;
          color: #606266;
        }
        
        :deep(table) {
          width: 100%;
          border-collapse: collapse;
          margin: 12px 0;
          
          th, td {
            padding: 8px 12px;
            border: 1px solid #e4e7ed;
          }
          
          th {
            background: #f5f7fa;
            font-weight: 600;
          }
        }
        
        :deep(a) {
          color: #409EFF;
          text-decoration: none;
          
          &:hover {
            text-decoration: underline;
          }
        }
        
        // Mermaid 图表样式
        :deep(.mermaid-diagram-container) {
          margin: 16px 0;
          padding: 16px;
          background: #fff;
          border-radius: 4px;
          border: 1px solid #e4e7ed;
          overflow-x: auto;
          text-align: center;
          
          svg {
            max-width: 100%;
            height: auto;
          }
        }
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
