<template>
  <el-pagination
    v-model:current-page="currentPage"
    v-model:page-size="pageSize"
    :total="total"
    :page-sizes="pageSizes"
    :layout="layout"
    :background="background"
    @size-change="handleSizeChange"
    @current-change="handleCurrentChange"
  />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  total: number
  page?: number
  size?: number
  pageSizes?: number[]
  layout?: string
  background?: boolean
}>(), {
  page: 1,
  size: 20,
  pageSizes: () => [10, 20, 50, 100],
  layout: 'total, sizes, prev, pager, next, jumper',
  background: true
})

const emit = defineEmits(['update:page', 'update:size', 'change'])

const currentPage = ref(props.page)
const pageSize = ref(props.size)

watch(() => props.page, (val) => {
  currentPage.value = val
})

watch(() => props.size, (val) => {
  pageSize.value = val
})

const handleSizeChange = (size: number) => {
  pageSize.value = size
  emit('update:size', size)
  emit('change', currentPage.value, size)
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  emit('update:page', page)
  emit('change', page, pageSize.value)
}
</script>

<style lang="scss" scoped>
.el-pagination {
  justify-content: center;
  margin-top: 20px;
}
</style>
