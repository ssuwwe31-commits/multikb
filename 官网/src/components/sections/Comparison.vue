<template>
  <section class="py-32 bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
    <div class="max-w-7xl mx-auto px-6 lg:px-8">
      <!-- Section Header -->
      <div class="text-center mb-20">
        <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 mb-6">
          <span class="text-sm font-medium text-blue-700 dark:text-blue-300">版本选择</span>
        </div>
        <h2 class="text-5xl md:text-6xl font-bold mb-6">
          <span class="bg-gradient-to-r from-gray-900 to-gray-600 dark:from-gray-100 dark:to-gray-400 bg-clip-text text-transparent">
            选择适合您的版本
          </span>
        </h2>
        <p class="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
          开源基础版免费使用，企业版提供高级功能与专业支持
        </p>
      </div>

      <!-- Comparison Cards -->
      <div class="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
        <!-- Open Source Edition -->
        <div class="relative p-8 rounded-2xl bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-300 hover:shadow-xl">
          <div class="text-center mb-8">
            <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-green-100 border border-green-200 mb-4">
              <span class="text-sm font-medium text-green-700">开源免费</span>
            </div>
            <h3 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">开源基础版</h3>
            <div class="text-5xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent mb-2">
              免费
            </div>
            <p class="text-gray-600 dark:text-gray-400">完整核心功能</p>
          </div>

          <ul class="space-y-4 mb-8">
            <li 
              v-for="feature in openSourceFeatures" 
              :key="feature"
              class="flex items-center space-x-3"
            >
              <svg class="w-6 h-6 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <span class="text-gray-700 dark:text-gray-300">{{ feature }}</span>
            </li>
          </ul>

          <router-link 
            to="/docs"
            class="block w-full px-6 py-3 bg-gray-900 dark:bg-gray-700 text-white rounded-xl font-semibold hover:bg-gray-800 dark:hover:bg-gray-600 transition-all duration-300 hover:shadow-lg text-center"
          >
            立即使用
          </router-link>
        </div>

        <!-- Enterprise Edition -->
        <div class="relative p-8 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 text-white border-2 border-blue-500 shadow-2xl transform scale-105">
          <!-- Badge -->
          <div class="absolute -top-4 left-1/2 transform -translate-x-1/2">
            <span class="px-4 py-1 bg-yellow-400 text-yellow-900 rounded-full text-sm font-bold shadow-lg">
              推荐
            </span>
          </div>

          <div class="text-center mb-8">
            <h3 class="text-3xl font-bold mb-2">企业版</h3>
            <div class="text-5xl font-bold mb-2">定制报价</div>
            <p class="text-blue-100">高级功能 + 专业支持</p>
          </div>

          <ul class="space-y-4 mb-8">
            <li 
              v-for="feature in enterpriseFeatures" 
              :key="feature"
              class="flex items-center space-x-3"
            >
              <svg class="w-6 h-6 text-yellow-300 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <span>{{ feature }}</span>
            </li>
          </ul>

          <router-link 
            to="/contact"
            class="block w-full px-6 py-3 bg-white text-blue-600 rounded-xl font-semibold hover:bg-gray-50 transition-all duration-300 hover:shadow-lg text-center"
          >
            联系销售
          </router-link>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const openSourceFeatures = [
  '9种文档格式支持',
  '多模态问答',
  '6种检索策略',
  '图片管理与OCR识别',
  '引用溯源',
  '流式输出',
  '智能分块',
  '会话管理',
  '搜索历史与建议',
  '处理进度追踪',
  '联网搜索'
]

const enterpriseFeatures = [
  '包含开源版所有功能',
  '安全扫描',
  '版本管理',
  '数据隔离',
  '知识图谱（自动实体提取）',
  '智能Agent（多步骤任务）',
  'K8s监控诊断',
  '知识库共享',
  '7×24小时技术支持'
]
</script>

