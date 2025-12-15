<template>
  <div class="cases-page">
    <Navbar />
    
    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto">
          <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 mb-6">
            <span class="text-sm font-medium text-blue-700 dark:text-blue-300">成功案例</span>
          </div>
          <h1 class="text-5xl md:text-6xl font-bold mb-6">
            <span class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
              用户案例
            </span>
          </h1>
          <p class="text-xl text-gray-600 dark:text-gray-300">
            看看我们的客户如何使用 Knowledge Base 提升团队协作效率
          </p>
        </div>
      </div>
    </section>

    <!-- Cases Grid -->
    <section class="py-20 bg-white dark:bg-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          <!-- Case 1 -->
          <div class="group relative p-8 rounded-2xl bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
            <div class="flex items-center space-x-4 mb-6">
              <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
                科技
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100">某大型科技公司</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400">互联网行业 · 5000+员工</p>
              </div>
            </div>
            
            <p class="text-gray-600 dark:text-gray-300 mb-6 leading-relaxed">
              "Multikb Base 帮助我们统一管理技术文档，研发团队可以快速查找API文档、技术规范和最佳实践。多模态检索功能让我们的技术文档搜索效率提升了80%。"
            </p>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                  <span class="text-gray-600 font-semibold">张</span>
                </div>
                <div>
                  <div class="text-sm font-semibold text-gray-900 dark:text-gray-100">张总</div>
                  <div class="text-xs text-gray-500">技术总监</div>
                </div>
              </div>
              <div class="flex space-x-1">
                <svg v-for="i in 5" :key="i" class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              </div>
            </div>

            <!-- Stats -->
            <div class="mt-6 pt-6 border-t border-gray-200">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <div class="text-2xl font-bold text-blue-600">80%</div>
                  <div class="text-xs text-gray-500">搜索效率提升</div>
                </div>
                <div>
                  <div class="text-2xl font-bold text-purple-600">5000+</div>
                  <div class="text-xs text-gray-500">活跃用户</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Case 2 -->
          <div class="group relative p-8 rounded-2xl bg-white border-2 border-gray-200 hover:border-blue-300 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
            <div class="flex items-center space-x-4 mb-6">
              <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-2xl font-bold">
                金融
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900">某知名金融机构</h3>
                <p class="text-sm text-gray-500">金融行业 · 2000+员工</p>
              </div>
            </div>
            
            <p class="text-gray-600 mb-6 leading-relaxed">
              "企业级安全是我们最看重的，Multikb Base 的 ClamAV 病毒扫描功能完全满足我们的合规要求。知识库的版本管理功能让我们可以追踪所有文档变更，审计非常方便。"
            </p>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                  <span class="text-gray-600 font-semibold">李</span>
                </div>
                <div>
                  <div class="text-sm font-semibold text-gray-900">李经理</div>
                  <div class="text-xs text-gray-500">信息安全负责人</div>
                </div>
              </div>
              <div class="flex space-x-1">
                <svg v-for="i in 5" :key="i" class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              </div>
            </div>

            <!-- Stats -->
            <div class="mt-6 pt-6 border-t border-gray-200">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <div class="text-2xl font-bold text-green-600">100%</div>
                  <div class="text-xs text-gray-500">合规要求满足</div>
                </div>
                <div>
                  <div class="text-2xl font-bold text-teal-600">2000+</div>
                  <div class="text-xs text-gray-500">文档管理</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Case 3 -->
          <div class="group relative p-8 rounded-2xl bg-white border-2 border-gray-200 hover:border-blue-300 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
            <div class="flex items-center space-x-4 mb-6">
              <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-2xl font-bold">
                教育
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900">某知名高校</h3>
                <p class="text-sm text-gray-500">教育行业 · 10000+师生</p>
              </div>
            </div>
            
            <p class="text-gray-600 mb-6 leading-relaxed">
              "我们使用 Multikb Base 管理课程资料、研究论文和教学资源。9种文档格式支持让我们可以统一管理PDF课件、Word教案、Excel成绩表等。多模态检索让师生可以快速找到需要的资料。"
            </p>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                  <span class="text-gray-600 font-semibold">王</span>
                </div>
                <div>
                  <div class="text-sm font-semibold text-gray-900">王教授</div>
                  <div class="text-xs text-gray-500">信息中心主任</div>
                </div>
              </div>
              <div class="flex space-x-1">
                <svg v-for="i in 5" :key="i" class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              </div>
            </div>

            <!-- Stats -->
            <div class="mt-6 pt-6 border-t border-gray-200">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <div class="text-2xl font-bold text-orange-600">10000+</div>
                  <div class="text-xs text-gray-500">活跃用户</div>
                </div>
                <div>
                  <div class="text-2xl font-bold text-red-600">5000+</div>
                  <div class="text-xs text-gray-500">文档资源</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Case 4 -->
          <div class="group relative p-8 rounded-2xl bg-white border-2 border-gray-200 hover:border-blue-300 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
            <div class="flex items-center space-x-4 mb-6">
              <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
                制造
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900">某制造企业</h3>
                <p class="text-sm text-gray-500">制造业 · 3000+员工</p>
              </div>
            </div>
            
            <p class="text-gray-600 mb-6 leading-relaxed">
              "我们使用 Multikb Base 管理产品手册、技术规范和操作指南。版本管理功能让我们可以追踪所有文档的变更历史，确保员工始终使用最新版本。图片搜索功能特别实用，可以通过产品图片快速找到相关文档。"
            </p>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                  <span class="text-gray-600 font-semibold">刘</span>
                </div>
                <div>
                  <div class="text-sm font-semibold text-gray-900">刘主任</div>
                  <div class="text-xs text-gray-500">技术文档负责人</div>
                </div>
              </div>
              <div class="flex space-x-1">
                <svg v-for="i in 5" :key="i" class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              </div>
            </div>

            <!-- Stats -->
            <div class="mt-6 pt-6 border-t border-gray-200">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <div class="text-2xl font-bold text-indigo-600">3000+</div>
                  <div class="text-xs text-gray-500">技术文档</div>
                </div>
                <div>
                  <div class="text-2xl font-bold text-purple-600">95%</div>
                  <div class="text-xs text-gray-500">文档准确率</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Case 5 -->
          <div class="group relative p-8 rounded-2xl bg-white border-2 border-gray-200 hover:border-blue-300 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
            <div class="flex items-center space-x-4 mb-6">
              <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center text-white text-2xl font-bold">
                医疗
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900">某三甲医院</h3>
                <p class="text-sm text-gray-500">医疗行业 · 5000+员工</p>
              </div>
            </div>
            
            <p class="text-gray-600 mb-6 leading-relaxed">
              "Multikb Base 帮助我们管理医疗指南、病例资料和培训文档。ClamAV 安全扫描确保所有上传的文档都是安全的，这对于医疗行业至关重要。多模态检索让医生可以通过文字或图片快速查找相关病例。"
            </p>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                  <span class="text-gray-600 font-semibold">陈</span>
                </div>
                <div>
                  <div class="text-sm font-semibold text-gray-900">陈主任</div>
                  <div class="text-xs text-gray-500">信息科主任</div>
                </div>
              </div>
              <div class="flex space-x-1">
                <svg v-for="i in 5" :key="i" class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              </div>
            </div>

            <!-- Stats -->
            <div class="mt-6 pt-6 border-t border-gray-200">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <div class="text-2xl font-bold text-pink-600">5000+</div>
                  <div class="text-xs text-gray-500">医疗文档</div>
                </div>
                <div>
                  <div class="text-2xl font-bold text-rose-600">99.9%</div>
                  <div class="text-xs text-gray-500">安全扫描率</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Case 6 -->
          <div class="group relative p-8 rounded-2xl bg-white border-2 border-gray-200 hover:border-blue-300 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
            <div class="flex items-center space-x-4 mb-6">
              <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-2xl font-bold">
                咨询
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900">某咨询公司</h3>
                <p class="text-sm text-gray-500">咨询行业 · 500+员工</p>
              </div>
            </div>
            
            <p class="text-gray-600 mb-6 leading-relaxed">
              "作为咨询公司，我们积累了大量的行业报告、案例研究和最佳实践。Multikb Base 的知识图谱功能帮助我们建立知识之间的关联，让顾问可以快速发现相关的案例和洞察。"
            </p>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                  <span class="text-gray-600 font-semibold">赵</span>
                </div>
                <div>
                  <div class="text-sm font-semibold text-gray-900">赵总</div>
                  <div class="text-xs text-gray-500">知识管理总监</div>
                </div>
              </div>
              <div class="flex space-x-1">
                <svg v-for="i in 5" :key="i" class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              </div>
            </div>

            <!-- Stats -->
            <div class="mt-6 pt-6 border-t border-gray-200">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <div class="text-2xl font-bold text-cyan-600">500+</div>
                  <div class="text-xs text-gray-500">行业报告</div>
                </div>
                <div>
                  <div class="text-2xl font-bold text-blue-600">200+</div>
                  <div class="text-xs text-gray-500">知识图谱节点</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Stats Section -->
    <section class="py-20 bg-gradient-to-br from-gray-50 to-blue-50">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-4xl font-bold text-gray-900 mb-4">数据统计</h2>
          <p class="text-xl text-gray-600">我们的客户取得的成果</p>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div class="text-center">
            <div class="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              100+
            </div>
            <div class="text-gray-600 font-medium">企业客户</div>
          </div>
          <div class="text-center">
            <div class="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              50万+
            </div>
            <div class="text-gray-600 font-medium">活跃用户</div>
          </div>
          <div class="text-center">
            <div class="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              100万+
            </div>
            <div class="text-gray-600 font-medium">管理文档</div>
          </div>
          <div class="text-center">
            <div class="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              95%
            </div>
            <div class="text-gray-600 font-medium">客户满意度</div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-20 bg-gradient-to-br from-blue-600 to-purple-600 text-white">
      <div class="max-w-4xl mx-auto px-6 lg:px-8 text-center">
        <h2 class="text-4xl md:text-5xl font-bold mb-6">
          加入我们的成功案例
        </h2>
        <p class="text-xl text-blue-100 mb-8">
          让 Multikb Base 帮助您的团队提升协作效率
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <button class="px-8 py-4 bg-white text-blue-600 rounded-xl font-semibold hover:bg-gray-50 transition-all duration-300 hover:shadow-lg">
            免费试用
          </button>
          <button class="px-8 py-4 bg-transparent border-2 border-white text-white rounded-xl font-semibold hover:bg-white/10 transition-all duration-300">
            联系销售
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
</script>

<style scoped>
.cases-page {
  min-height: 100vh;
}
</style>

