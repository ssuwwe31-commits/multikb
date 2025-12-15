<template>
  <div class="api-search">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">搜索API</h1>
      <p class="text-xl text-gray-600">文本搜索、向量搜索、混合搜索等接口</p>
    </div>

    <section class="mb-16">
      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">/api/v1/search</code>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">搜索接口</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">基础搜索</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/search/</p>
          <p class="text-sm text-gray-600 mb-3">支持关键词、语义、混合搜索 + Rerank精排</p>
          <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto">
            <code>{
  "query": "搜索关键词",
  "search_type": "hybrid",
  "knowledge_base_id": 1,
  "top_k": 10
}</code>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">向量搜索</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/search/vector</p>
          <p class="text-sm text-gray-600">基于语义相似度的向量搜索</p>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">混合搜索</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/search/hybrid</p>
          <p class="text-sm text-gray-600">结合向量和关键词的混合搜索</p>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">高级搜索</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/search/advanced</p>
          <p class="text-sm text-gray-600">支持多条件组合的高级搜索</p>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">📊</div>
        <h2 class="text-3xl font-bold text-gray-900">其他功能</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">搜索建议</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/search/suggestions</p>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">搜索历史</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/search/history</p>
        </div>
        <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">相似搜索</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/search/similar</p>
        </div>
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">搜索分面</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/search/facets</p>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-overview" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">API概览 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

