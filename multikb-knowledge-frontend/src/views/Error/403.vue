<template>
  <BaseError :status="403" message="您没有权限访问此页面" />
</template>

<script setup lang="ts">
import BaseError from '@/components/common/BaseError.vue'
</script>
