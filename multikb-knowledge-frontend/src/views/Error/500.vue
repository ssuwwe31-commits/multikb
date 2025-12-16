<template>
  <BaseError :status="500" message="服务器内部错误，请稍后再试" />
</template>

<script setup lang="ts">
import BaseError from '@/components/common/BaseError.vue'
</script>
