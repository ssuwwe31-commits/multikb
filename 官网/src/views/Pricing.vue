<template>
  <div class="pricing-page">
    <Navbar />
    
    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto">
          <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 mb-6">
            <span class="text-sm font-medium text-blue-700 dark:text-blue-300">定价方案</span>
          </div>
          <h1 class="text-5xl md:text-6xl font-bold mb-6">
            <span class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
              选择适合您的方案
            </span>
          </h1>
          <p class="text-xl text-gray-600 dark:text-gray-300">
            开源基础版免费使用，企业版提供高级功能与专业支持
          </p>
        </div>
      </div>
    </section>

    <!-- Pricing Cards -->
    <section class="py-20 bg-white dark:bg-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <!-- Open Source Edition -->
          <div class="relative p-8 rounded-2xl bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-300 hover:shadow-xl">
            <div class="text-center mb-8">
              <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-green-100 border border-green-200 mb-4">
                <span class="text-sm font-medium text-green-700">开源免费</span>
              </div>
              <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">开源基础版</h3>
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

            <button class="w-full px-6 py-3 bg-gray-900 text-white rounded-xl font-semibold hover:bg-gray-800 transition-all duration-300 hover:shadow-lg">
              立即使用
            </button>
          </div>

          <!-- Standard Edition -->
          <div class="relative p-8 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 text-white border-2 border-blue-500 shadow-2xl transform scale-105">
            <!-- Badge -->
            <div class="absolute -top-4 left-1/2 transform -translate-x-1/2">
              <span class="px-4 py-1 bg-yellow-400 text-yellow-900 rounded-full text-sm font-bold shadow-lg">
                推荐
              </span>
            </div>

            <div class="text-center mb-8">
              <h3 class="text-2xl font-bold mb-2">标准版</h3>
              <div class="text-5xl font-bold mb-2">15万/年</div>
              <p class="text-blue-100">适合中小型企业</p>
            </div>

            <ul class="space-y-4 mb-8">
              <li 
                v-for="feature in standardFeatures" 
                :key="feature"
                class="flex items-center space-x-3"
              >
                <svg class="w-6 h-6 text-yellow-300 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>{{ feature }}</span>
              </li>
            </ul>

            <button class="w-full px-6 py-3 bg-white text-blue-600 rounded-xl font-semibold hover:bg-gray-50 transition-all duration-300 hover:shadow-lg">
              联系销售
            </button>
          </div>

          <!-- Enterprise Edition -->
          <div class="relative p-8 rounded-2xl bg-white border-2 border-gray-200 hover:border-purple-300 transition-all duration-300 hover:shadow-xl">
            <div class="text-center mb-8">
              <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-purple-100 border border-purple-200 mb-4">
                <span class="text-sm font-medium text-purple-700">企业定制</span>
              </div>
              <h3 class="text-2xl font-bold text-gray-900 mb-2">企业版</h3>
              <div class="text-5xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent mb-2">
                定制报价
              </div>
              <p class="text-gray-600">适合大型企业</p>
            </div>

            <ul class="space-y-4 mb-8">
              <li 
                v-for="feature in enterpriseFeatures" 
                :key="feature"
                class="flex items-center space-x-3"
              >
                <svg class="w-6 h-6 text-purple-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span class="text-gray-700 dark:text-gray-300">{{ feature }}</span>
              </li>
            </ul>

            <button class="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300">
              联系销售
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Feature Comparison Table -->
    <section class="py-20 bg-gray-50">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-4xl font-bold text-gray-900 mb-4">功能对比</h2>
          <p class="text-xl text-gray-600">详细的功能对比，帮助您做出最佳选择</p>
        </div>

        <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-4 text-left text-sm font-semibold text-gray-900">功能</th>
                  <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900">开源版</th>
                  <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900">标准版</th>
                  <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900">企业版</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="row in comparisonTable" :key="row.feature" class="hover:bg-gray-50">
                  <td class="px-6 py-4 text-sm font-medium text-gray-900">{{ row.feature }}</td>
                  <td class="px-6 py-4 text-center">
                    <span v-if="row.openSource" class="text-green-500 text-xl">✓</span>
                    <span v-else class="text-gray-400 text-xl">—</span>
                  </td>
                  <td class="px-6 py-4 text-center">
                    <span v-if="row.standard" class="text-green-500 text-xl">✓</span>
                    <span v-else class="text-gray-400 text-xl">—</span>
                  </td>
                  <td class="px-6 py-4 text-center">
                    <span v-if="row.enterprise" class="text-green-500 text-xl">✓</span>
                    <span v-else class="text-gray-400 text-xl">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-20 bg-gradient-to-br from-blue-600 to-purple-600 text-white">
      <div class="max-w-4xl mx-auto px-6 lg:px-8 text-center">
        <h2 class="text-4xl md:text-5xl font-bold mb-6">
          还有疑问？
        </h2>
        <p class="text-xl text-blue-100 mb-8">
          我们的销售团队随时为您解答问题，帮助您选择最适合的方案
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <button class="px-8 py-4 bg-white text-blue-600 rounded-xl font-semibold hover:bg-gray-50 transition-all duration-300 hover:shadow-lg">
            联系销售
          </button>
          <button class="px-8 py-4 bg-transparent border-2 border-white text-white rounded-xl font-semibold hover:bg-white/10 transition-all duration-300">
            查看文档
          </button>
        </div>
      </div>
    </section>

    <Footer />
  </div>
</template>

<script setup lang="ts">
import Navbar from '../components/layout/Navbar.vue'
import Footer from '../components/layout/Footer.vue'

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
  '联网搜索',
  '社区支持'
]

const standardFeatures = [
  '包含开源版所有功能',
  '安全扫描',
  '版本管理',
  '数据隔离',
  '知识图谱',
  '智能Agent',
  'K8s监控诊断',
  '知识库共享',
  '高级权限管理',
  '技术支持（工作时间）'
]

const enterpriseFeatures = [
  '包含标准版所有功能',
  '无限制用户数',
  '无限制知识库',
  '定制开发',
  '7×24小时技术支持',
  'SLA保障',
  '专属客户经理'
]

const comparisonTable = [
  { feature: '9种文档格式', openSource: true, standard: true, enterprise: true },
  { feature: '多模态问答', openSource: true, standard: true, enterprise: true },
  { feature: '6种检索策略', openSource: true, standard: true, enterprise: true },
  { feature: '图片管理与OCR', openSource: true, standard: true, enterprise: true },
  { feature: '引用溯源', openSource: true, standard: true, enterprise: true },
  { feature: '流式输出', openSource: true, standard: true, enterprise: true },
  { feature: '智能分块', openSource: true, standard: true, enterprise: true },
  { feature: '会话管理', openSource: true, standard: true, enterprise: true },
  { feature: '搜索历史与建议', openSource: true, standard: true, enterprise: true },
  { feature: '处理进度追踪', openSource: true, standard: true, enterprise: true },
  { feature: '联网搜索', openSource: true, standard: true, enterprise: true },
  { feature: '安全扫描', openSource: false, standard: true, enterprise: true },
  { feature: '数据隔离', openSource: false, standard: true, enterprise: true },
  { feature: '版本管理', openSource: false, standard: true, enterprise: true },
  { feature: '知识图谱', openSource: false, standard: true, enterprise: true },
  { feature: '智能Agent', openSource: false, standard: true, enterprise: true },
  { feature: 'K8s监控诊断', openSource: false, standard: true, enterprise: true },
  { feature: '知识库共享', openSource: false, standard: true, enterprise: true },
  { feature: '高级权限管理', openSource: false, standard: true, enterprise: true },
  { feature: '定制开发', openSource: false, standard: false, enterprise: true },
  { feature: '7×24技术支持', openSource: false, standard: false, enterprise: true },
  { feature: 'SLA保障', openSource: false, standard: false, enterprise: true }
]
</script>

<style scoped>
.pricing-page {
  min-height: 100vh;
}
</style>

