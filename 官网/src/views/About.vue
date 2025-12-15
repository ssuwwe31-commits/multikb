<template>
  <div class="about-page">
    <Navbar />
    
    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto">
          <h1 class="text-5xl md:text-6xl font-bold mb-6">
            <span class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
              关于我们
            </span>
          </h1>
          <p class="text-xl text-gray-600 dark:text-gray-300">
            致力于为企业提供最专业的知识库管理解决方案
          </p>
        </div>
      </div>
    </section>

    <!-- Content Section -->
    <section class="py-20 bg-white dark:bg-gray-900">
      <div class="max-w-4xl mx-auto px-6 lg:px-8">
        <div class="prose prose-lg dark:prose-invert max-w-none">
          <!-- Mission -->
          <div class="mb-16">
            <h2 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">我们的使命</h2>
            <p class="text-lg text-gray-700 dark:text-gray-300 leading-relaxed mb-4">
              Multikb Base 致力于帮助企业构建高效、安全、智能的知识管理体系。我们相信，知识是企业最宝贵的资产，通过先进的技术手段，我们可以让知识的获取、管理和应用变得更加简单和高效。
            </p>
            <p class="text-lg text-gray-700 dark:text-gray-300 leading-relaxed">
              我们的使命是成为企业知识管理的首选平台，通过持续的技术创新和产品优化，帮助企业在数字化转型的道路上走得更远。
            </p>
          </div>

          <!-- Vision -->
          <div class="mb-16">
            <h2 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">我们的愿景</h2>
            <p class="text-lg text-gray-700 dark:text-gray-300 leading-relaxed mb-4">
              成为全球领先的企业级知识库管理平台，让每一家企业都能轻松构建自己的知识体系，实现知识的价值最大化。
            </p>
            <p class="text-lg text-gray-700 dark:text-gray-300 leading-relaxed">
              我们希望通过开放、共享的方式，与全球开发者共同推动知识管理技术的发展，让知识管理成为每个企业的核心竞争力。
            </p>
          </div>

          <!-- Values -->
          <div class="mb-16">
            <h2 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">我们的价值观</h2>
            <div class="grid md:grid-cols-2 gap-8">
              <div class="p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-2 border-blue-100 dark:border-blue-800">
                <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">开放创新</h3>
                <p class="text-gray-700 dark:text-gray-300">
                  我们相信开源的力量，通过开放源代码和社区协作，推动技术创新和产品发展。
                </p>
              </div>
              <div class="p-6 rounded-xl bg-gradient-to-br from-green-50 to-teal-50 dark:from-green-900/20 dark:to-teal-900/20 border-2 border-green-100 dark:border-green-800">
                <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">用户至上</h3>
                <p class="text-gray-700 dark:text-gray-300">
                  用户的需求是我们产品发展的方向，我们始终以用户体验为核心，持续优化产品功能。
                </p>
              </div>
              <div class="p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-2 border-purple-100 dark:border-purple-800">
                <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">安全可靠</h3>
                <p class="text-gray-700 dark:text-gray-300">
                  企业级安全是我们的底线，我们采用最先进的安全技术，保障用户数据的安全和隐私。
                </p>
              </div>
              <div class="p-6 rounded-xl bg-gradient-to-br from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 border-2 border-orange-100 dark:border-orange-800">
                <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">持续改进</h3>
                <p class="text-gray-700 dark:text-gray-300">
                  我们不断学习、不断改进，通过快速迭代和持续优化，为用户提供更好的产品体验。
                </p>
              </div>
            </div>
          </div>

          <!-- Technology -->
          <div class="mb-16">
            <h2 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">技术实力</h2>
            <p class="text-lg text-gray-700 dark:text-gray-300 leading-relaxed mb-6">
              Multikb Base 基于最新的技术栈构建，采用现代化的架构设计，确保系统的高性能、高可用和高扩展性。
            </p>
            <div class="grid md:grid-cols-3 gap-6">
              <div class="text-center p-6 rounded-xl bg-gray-50 dark:bg-gray-800">
                <div class="text-4xl font-bold text-blue-600 dark:text-blue-400 mb-2">100+</div>
                <div class="text-gray-600 dark:text-gray-400">API接口</div>
              </div>
              <div class="text-center p-6 rounded-xl bg-gray-50 dark:bg-gray-800">
                <div class="text-4xl font-bold text-purple-600 dark:text-purple-400 mb-2">9种</div>
                <div class="text-gray-600 dark:text-gray-400">文档格式</div>
              </div>
              <div class="text-center p-6 rounded-xl bg-gray-50 dark:bg-gray-800">
                <div class="text-4xl font-bold text-green-600 dark:text-green-400 mb-2">6种</div>
                <div class="text-gray-600 dark:text-gray-400">检索策略</div>
              </div>
            </div>
          </div>

          <!-- Contact -->
          <div class="text-center p-8 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-2 border-blue-100 dark:border-blue-800">
            <h2 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">加入我们</h2>
            <p class="text-lg text-gray-700 dark:text-gray-300 mb-6">
              如果您对我们的产品感兴趣，或者想要了解更多信息，欢迎与我们联系。
            </p>
            <router-link 
              to="/contact"
              class="inline-block px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-semibold hover:shadow-lg transition-all duration-300"
            >
              联系我们
            </router-link>
          </div>
        </div>
      </div>
    </section>
    
    <Footer />
  </div>
</template>

<script setup lang="ts">
import Navbar from '../components/layout/Navbar.vue'
import Footer from '../components/layout/Footer.vue'
</script>

<style scoped>
.about-page {
  min-height: 100vh;
}
</style>

