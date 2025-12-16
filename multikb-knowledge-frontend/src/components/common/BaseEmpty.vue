<template>
  <el-empty :description="description" :image-size="imageSize">
    <template #image>
      <slot name="image" />
    </template>
    <template #description>
      <slot name="description" />
    </template>
    <template #extra>
      <slot name="extra">
        <el-button v-if="showAction" @click="$emit('action')">{{ actionText }}</el-button>
      </slot>
    </template>
  </el-empty>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  description?: string
  imageSize?: number
  showAction?: boolean
  actionText?: string
}>(), {
  description: '暂无数据',
  imageSize: 200,
  showAction: false,
  actionText: '新建'
})

defineEmits(['action'])
</script>

<style lang="scss" scoped>
.el-empty {
  padding: 40px 0;
}
</style>
