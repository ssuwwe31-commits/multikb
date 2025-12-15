<template>
  <div class="contact-page">
    <Navbar />
    
    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto">
          <h1 class="text-5xl md:text-6xl font-bold mb-6">
            <span class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
              联系我们
            </span>
          </h1>
          <p class="text-xl text-gray-600 dark:text-gray-300">
            有任何问题或需要帮助？我们随时为您服务
          </p>
        </div>
      </div>
    </section>

    <!-- Contact Information -->
    <section class="py-20 bg-white dark:bg-gray-900">
      <div class="max-w-4xl mx-auto px-6 lg:px-8">
        <div class="grid md:grid-cols-2 gap-6">
          <!-- Email Card -->
          <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 hover:shadow-2xl transition-all duration-300 border border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-center w-16 h-16 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl">
              <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 text-center mb-3">邮箱联系</h3>
            <div class="text-center mb-6">
              <a 
                href="mailto:sujiejie007@163.com"
                class="text-lg text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium break-all transition-colors"
              >
                sujiejie007@163.com
              </a>
            </div>
            <button
              @click="copyToClipboard('sujiejie007@163.com')"
              class="w-full px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm font-medium"
            >
              复制邮箱
            </button>
          </div>

          <!-- QQ Card -->
          <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 hover:shadow-2xl transition-all duration-300 border border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-center w-16 h-16 mx-auto mb-6 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl">
              <svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            </div>
            <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 text-center mb-3">QQ联系</h3>
            <div class="text-center mb-6">
              <span class="text-lg text-gray-900 dark:text-gray-100 font-medium">
                736374160
              </span>
            </div>
            <a
              :href="`https://wpa.qq.com/msgrd?v=3&uin=736374160&site=qq&menu=yes`"
              target="_blank"
              rel="noopener noreferrer"
              class="block w-full px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 transition-all text-center text-sm font-medium shadow-lg hover:shadow-xl"
            >
              打开QQ聊天
            </a>
          </div>
        </div>

        <!-- Additional Info -->
        <div class="mt-12 text-center">
          <p class="text-gray-600 dark:text-gray-400 text-lg">
            请通过以上方式联系我们，我们会尽快回复您的问题
          </p>
        </div>
      </div>
    </section>
    
    <Footer />
  </div>
</template>

<script setup lang="ts">
import Navbar from '../components/layout/Navbar.vue'
import Footer from '../components/layout/Footer.vue'

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    // 可以添加提示消息
    alert('已复制到剪贴板')
  } catch (err) {
    // 降级方案
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.opacity = '0'
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      alert('已复制到剪贴板')
    } catch (err) {
      alert('复制失败，请手动复制')
    }
    document.body.removeChild(textArea)
  }
}
</script>

<style scoped>
.contact-page {
  min-height: 100vh;
}
</style>

