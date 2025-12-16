<template>
  <div class="base-error">
    <el-result
      :icon="icon"
      :title="title"
      :sub-title="subTitle"
    >
      <template #extra>
        <el-button type="primary" @click="$emit('retry')">重试</el-button>
        <el-button @click="$emit('back')">返回</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { CircleClose, Warning } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  status?: number
  message?: string
}>(), {
  status: 500,
  message: '未知错误'
})

const emit = defineEmits(['retry', 'back'])

const icon = computed(() => {
  return props.status === 403 ? Warning : CircleClose
})

const title = computed(() => {
  const map: Record<number, string> = {
    403: '访问被拒绝',
    404: '页面不存在',
    500: '服务器错误'
  }
  return map[props.status] || '发生错误'
})

const subTitle = computed(() => {
  return props.message || '请稍后再试'
})
</script>

<style lang="scss" scoped>
.base-error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
