<template>
  <div v-if="loading" class="base-loading">
    <el-icon class="is-loading">
      <loading />
    </el-icon>
    <div v-if="text" class="loading-text">{{ text }}</div>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'

defineProps<{
  loading: boolean
  text?: string
}>()
</script>

<style lang="scss" scoped>
.base-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;

  .el-icon {
    font-size: 32px;
  }

  .loading-text {
    margin-top: 16px;
    color: #909399;
    font-size: 14px;
  }
}
</style>
