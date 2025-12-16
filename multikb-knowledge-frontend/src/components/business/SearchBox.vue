<template>
  <div class="search-box">
    <el-input
      v-model="query"
      :placeholder="placeholder"
      @input="handleInput"
      @keyup.enter="handleSearch"
      clearable
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
      <template #append>
        <el-button @click="handleSearch">搜索</el-button>
      </template>
    </el-input>

    <div v-if="suggestions.length > 0" class="suggestions">
      <div
        v-for="suggestion in suggestions"
        :key="suggestion"
        class="suggestion-item"
        @click="handleSuggestionClick(suggestion)"
      >
        {{ suggestion }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { debounce } from '@/utils/common'

const props = withDefaults(defineProps<{
  placeholder?: string
  suggestions?: string[]
}>(), {
  placeholder: '请输入搜索关键词...',
  suggestions: () => []
})

const emit = defineEmits(['search', 'input'])

const query = ref('')

const handleInput = debounce((value: string) => {
  emit('input', value)
}, 300)

const handleSearch = () => {
  emit('search', query.value)
}

const handleSuggestionClick = (suggestion: string) => {
  query.value = suggestion
  handleSearch()
}
</script>

<style lang="scss" scoped>
.search-box {
  position: relative;

  .suggestions {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: #fff;
    border: 1px solid #e5e5e5;
    border-radius: 4px;
    margin-top: 4px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 10;

    .suggestion-item {
      padding: 10px 15px;
      cursor: pointer;
      transition: background-color 0.3s;

      &:hover {
        background-color: #f5f5f5;
      }
    }
  }
}
</style>
