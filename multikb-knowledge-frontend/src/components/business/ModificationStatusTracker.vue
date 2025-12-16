<template>
  <el-drawer
    v-model="visible"
    title="修改状态跟踪"
    direction="rtl"
    size="400px"
  >
    <div class="status-tracker">
      <!-- 当前任务状态 -->
      <el-card class="status-card">
        <template #header>
          <span>当前操作</span>
        </template>
        
        <el-steps :active="currentStep" direction="vertical">
          <el-step
            v-for="(step, index) in steps"
            :key="index"
            :title="step.title"
            :description="step.description"
            :status="step.status"
          >
            <template #icon>
              <el-icon v-if="step.icon">
                <component :is="step.icon" />
              </el-icon>
            </template>
          </el-step>
        </el-steps>
      </el-card>

      <!-- 进度信息 -->
      <el-card class="progress-card" v-if="hasProgress">
        <template #header>
          <span>处理进度</span>
        </template>
        
        <el-progress
          :percentage="progressPercentage"
          :status="progressStatus"
        />
        <div class="progress-info">
          <span>{{ progressInfo }}</span>
        </div>
      </el-card>

      <!-- 任务日志 -->
      <el-card class="log-card">
        <template #header>
          <span>操作日志</span>
        </template>
        
        <el-scrollbar height="300px">
          <div class="log-item" v-for="(log, index) in logs" :key="index">
            <el-tag :type="getLogType(log.level)" size="small">
              {{ log.level }}
            </el-tag>
            <span class="log-time">{{ formatTime(log.time) }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </el-scrollbar>
      </el-card>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Check, Clock, Loading, SuccessFilled, CircleClose } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{
  visible?: boolean
}>()

const emit = defineEmits(['update:visible', 'close'])

const currentStep = ref(0)
const logs = ref<Array<{ level: string; message: string; time: string }>>([])
const hasProgress = ref(false)
const progressPercentage = ref(0)
const progressInfo = ref('')
const progressStatus = ref<'success' | 'exception' | 'warning' | undefined>()

const steps = computed(() => [
  {
    title: '内容验证',
    description: '验证修改内容格式和完整性',
    status: 'wait' as const,
    icon: undefined
  },
  {
    title: '保存修改',
    description: '保存块内容到数据库',
    status: 'wait' as const,
    icon: undefined
  },
  {
    title: '重新向量化',
    description: '仅对当前分块重新向量化',
    status: 'wait' as const,
    icon: undefined
  },
  {
    title: '更新索引',
    description: '更新OpenSearch索引',
    status: 'wait' as const,
    icon: undefined
  },
  {
    title: '更新缓存',
    description: '更新Redis缓存',
    status: 'wait' as const,
    icon: undefined
  },
  {
    title: '版本记录',
    description: '记录修改版本',
    status: 'wait' as const,
    icon: undefined
  }
])

const addLog = (level: string, message: string) => {
  logs.value.push({
    level,
    message,
    time: new Date().toISOString()
  })
}

const updateStep = (index: number, status: 'wait' | 'process' | 'finish' | 'error') => {
  if (steps.value[index]) {
    steps.value[index].status = status
    
    switch (status) {
      case 'process':
        steps.value[index].icon = Loading
        break
      case 'finish':
        steps.value[index].icon = SuccessFilled
        break
      case 'error':
        steps.value[index].icon = CircleClose
        break
      default:
        steps.value[index].icon = Clock
    }
  }
}

const updateProgress = (percentage: number, info: string, status?: 'success' | 'exception' | 'warning') => {
  progressPercentage.value = percentage
  progressInfo.value = info
  progressStatus.value = status
  hasProgress.value = true
}

const startModification = () => {
  currentStep.value = 0
  logs.value = []
  hasProgress.value = false
  progressPercentage.value = 0
  progressInfo.value = ''
  
  // 重置所有步骤
  steps.value.forEach((step, index) => {
    updateStep(index, 'wait')
  })
  
  addLog('info', '开始修改操作')
}

const finishStep = (stepIndex: number, message: string) => {
  updateStep(stepIndex, 'finish')
  addLog('success', message)
  if (stepIndex < steps.value.length - 1) {
    currentStep.value = stepIndex + 1
    updateStep(currentStep.value, 'process')
  }
}

const errorStep = (stepIndex: number, message: string) => {
  updateStep(stepIndex, 'error')
  addLog('error', message)
}

const getLogType = (level: string) => {
  const map: Record<string, string> = {
    info: '',
    success: 'success',
    warning: 'warning',
    error: 'danger'
  }
  return map[level] || ''
}

const formatTime = (time: string) => {
  return formatDateTime(time)
}

// 暴露方法供父组件调用
defineExpose({
  startModification,
  finishStep,
  errorStep,
  addLog,
  updateProgress,
  updateStep
})
</script>

<style lang="scss" scoped>
.status-tracker {
  .status-card {
    margin-bottom: 20px;
  }

  .progress-card {
    margin-bottom: 20px;
    
    .progress-info {
      margin-top: 10px;
      font-size: 14px;
      color: #666;
    }
  }

  .log-card {
    .log-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
      border-bottom: 1px solid #f0f0f0;

      .log-time {
        font-size: 12px;
        color: #999;
        min-width: 100px;
      }

      .log-message {
        flex: 1;
        font-size: 14px;
      }
    }
  }
}
</style>
