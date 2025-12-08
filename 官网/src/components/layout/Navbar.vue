<template>
  <nav 
    class="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
    :class="isScrolled ? 'bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl shadow-sm' : 'bg-transparent dark:bg-transparent'"
  >
    <div class="max-w-7xl mx-auto px-6 lg:px-8">
      <div class="flex items-center justify-between h-20">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span class="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Knowledge Base
          </span>
        </router-link>

        <!-- Navigation Links -->
        <div class="hidden md:flex items-center space-x-1">
          <router-link 
            v-for="link in navLinks" 
            :key="link.name"
            :to="link.path"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
            :class="isActive(link.path) 
              ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 font-semibold' 
              : 'text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-50 dark:hover:bg-gray-800'"
          >
            {{ link.name }}
          </router-link>
        </div>

        <!-- Actions -->
        <div class="flex items-center space-x-4">
          <!-- Search -->
          <button 
            @click="showSearch = true"
            class="hidden md:flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all duration-200 cursor-pointer"
          >
            <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span class="text-sm text-gray-500 dark:text-gray-400">搜索</span>
            <kbd class="px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded">⌘K</kbd>
          </button>

          <!-- CTA Button -->
          <router-link 
            to="/docs"
            class="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:shadow-lg hover:scale-105 transition-all duration-200"
          >
            开始使用
          </router-link>

          <!-- Theme Toggle -->
          <button 
            @click.stop="handleToggleDark"
            type="button"
            class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer relative z-10"
            :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
            aria-label="切换夜间模式"
          >
            <!-- Moon Icon (Dark Mode) -->
            <svg 
              v-if="!isDark"
              class="w-5 h-5 text-gray-600 dark:text-gray-300" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
            <!-- Sun Icon (Light Mode) -->
            <svg 
              v-else
              class="w-5 h-5 text-gray-300 dark:text-yellow-400" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Search Modal -->
    <SearchModal v-model:isOpen="showSearch" />
  </nav>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import SearchModal from './SearchModal.vue'

const route = useRoute()
const isScrolled = ref(false)
const showSearch = ref(false)

// Dark mode - 使用简单的ref和手动DOM操作
const isDark = ref(false)

// 初始化dark模式状态
const initDarkMode = () => {
  if (typeof window === 'undefined') return
  
  const html = document.documentElement
  
  // 先检查localStorage
  const saved = window.localStorage?.getItem('vueuse-color-scheme')
  
  if (saved === 'dark') {
    html.classList.add('dark')
    isDark.value = true
  } else if (saved === 'light') {
    html.classList.remove('dark')
    isDark.value = false
  } else {
    // 如果没有保存的值，检查系统偏好
    const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
    if (prefersDark) {
      html.classList.add('dark')
      isDark.value = true
      window.localStorage?.setItem('vueuse-color-scheme', 'dark')
    } else {
      html.classList.remove('dark')
      isDark.value = false
      window.localStorage?.setItem('vueuse-color-scheme', 'light')
    }
  }
}

const handleToggleDark = () => {
  const html = document.documentElement
  
  // 切换状态
  isDark.value = !isDark.value
  
  // 根据新状态更新DOM
  if (isDark.value) {
    html.classList.add('dark')
    window.localStorage?.setItem('vueuse-color-scheme', 'dark')
  } else {
    html.classList.remove('dark')
    window.localStorage?.setItem('vueuse-color-scheme', 'light')
  }
  
  console.log('Dark mode toggled:', isDark.value, 'HTML classes:', html.className)
}

const navLinks = [
  { name: '首页', path: '/' },
  { name: '功能', path: '/features' },
  { name: '文档', path: '/docs' },
  { name: '定价', path: '/pricing' },
  { name: '案例', path: '/cases' },
  { name: '联系我们', path: '/contact' }
]

const isActive = (path: string) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

const handleScroll = () => {
  isScrolled.value = window.scrollY > 20
}

onMounted(() => {
  // 初始化dark模式
  initDarkMode()
  
  // 添加滚动监听
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

