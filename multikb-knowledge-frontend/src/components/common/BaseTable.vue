<template>
  <el-table
    :data="data"
    :loading="loading"
    :border="border"
    :stripe="stripe"
    :highlight-current-row="highlightCurrentRow"
    @selection-change="$emit('selection-change', $event)"
    @row-click="$emit('row-click', $event)"
  >
    <el-table-column v-if="showSelection" type="selection" width="55" />
    <el-table-column v-if="showIndex" type="index" label="序号" width="80" />
    <slot />
  </el-table>

  <BasePagination
    v-if="showPagination && total > 0"
    v-model:page="currentPage"
    v-model:size="currentSize"
    :total="total"
    :page-sizes="pageSizes"
    @change="handlePageChange"
  />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import BasePagination from './BasePagination.vue'

const props = withDefaults(defineProps<{
  data: any[]
  loading?: boolean
  border?: boolean
  stripe?: boolean
  highlightCurrentRow?: boolean
  showSelection?: boolean
  showIndex?: boolean
  showPagination?: boolean
  total?: number
  page?: number
  size?: number
  pageSizes?: number[]
}>(), {
  loading: false,
  border: true,
  stripe: false,
  highlightCurrentRow: false,
  showSelection: false,
  showIndex: true,
  showPagination: true,
  total: 0,
  page: 1,
  size: 20,
  pageSizes: () => [10, 20, 50, 100]
})

const emit = defineEmits(['selection-change', 'row-click', 'page-change'])

const currentPage = ref(props.page)
const currentSize = ref(props.size)

watch(() => props.page, (val) => { currentPage.value = val })
watch(() => props.size, (val) => { currentSize.value = val })

const handlePageChange = (page: number, size: number) => {
  emit('page-change', page, size)
}
</script>

<style lang="scss" scoped>
// Base Table styles
</style>
