<template>
  <div class="advanced-k8s-monitoring">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">K8s监控</h1>
      <p class="text-xl text-gray-600">K8s集群监控和自动诊断（企业版）</p>
    </div>

    <div class="mb-6 p-4 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
      <div class="flex items-start space-x-3">
        <svg class="w-6 h-6 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        <div>
          <div class="font-semibold text-yellow-900 mb-1">企业版功能</div>
          <div class="text-sm text-yellow-800">K8s监控功能仅在企业版中提供，需要企业版License。</div>
        </div>
      </div>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">☸️</div>
        <h2 class="text-3xl font-bold text-gray-900">集群监控</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">集群管理</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>添加和管理K8s集群</li>
              <li>集群健康检查</li>
              <li>连接测试</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">资源监控</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>Pod资源使用情况</li>
              <li>Node资源监控</li>
              <li>Namespace资源统计</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">指标查询</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>CPU、内存、网络指标</li>
              <li>自定义指标查询</li>
              <li>指标历史趋势</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">自动诊断</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">智能诊断</h3>
            <p class="text-sm text-gray-700 mb-3">使用LLM分析集群问题，提供根因分析和解决方案</p>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>收集指标、日志、事件数据</li>
              <li>LLM分析问题根因</li>
              <li>提供解决方案建议</li>
              <li>支持多轮迭代诊断</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">诊断记录</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>查看诊断历史</li>
              <li>诊断报告导出</li>
              <li>诊断反馈和改进</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/pricing" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">了解企业版 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

