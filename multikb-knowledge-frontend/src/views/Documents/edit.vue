<template>
  <div class="document-edit-page">
    <ChunkEditor
      :document-id="documentId"
      @close="handleClose"
    />
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import ChunkEditor from '@/components/business/ChunkEditor.vue'

const route = useRoute()
const router = useRouter()
const documentId = Number(route.params.id)

const handleClose = () => {
  router.back()
}
</script>

<style lang="scss" scoped>
.document-edit-page {
  height: 100vh;
}
</style>
