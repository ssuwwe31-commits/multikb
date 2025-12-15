<template>
  <div class="api-image">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">图片API</h1>
      <p class="text-xl text-gray-600">图片上传、OCR识别、图片搜索等接口</p>
    </div>

    <section class="mb-16">
      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">/api/v1/images</code>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🖼️</div>
        <h2 class="text-3xl font-bold text-gray-900">图片管理</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">上传图片</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/images/upload</p>
          <p class="text-sm text-gray-600 mb-3">上传图片文件，自动进行OCR识别和向量化</p>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">获取图片列表</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/images/</p>
          <p class="text-sm text-gray-600">获取图片列表，支持分页和筛选</p>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">获取图片详情</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/images/{image_id}</p>
          <p class="text-sm text-gray-600">获取指定图片的详细信息</p>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">图片搜索</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">以图搜图</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/images/search-by-image</p>
          <p class="text-sm text-gray-600">上传图片，搜索相似图片</p>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">文本搜图</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/images/search-by-text</p>
          <p class="text-sm text-gray-600">使用文本描述搜索图片</p>
        </div>
        <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">相似图片</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/images/similar/{image_id}</p>
          <p class="text-sm text-gray-600">获取与指定图片相似的图片</p>
        </div>
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">上传并搜索</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/images/upload-and-search</p>
          <p class="text-sm text-gray-600">上传图片并立即搜索相似图片</p>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">🔧</div>
        <h2 class="text-3xl font-bold text-gray-900">OCR功能</h2>
      </div>

      <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">重新OCR识别</h3>
        <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/images/{image_id}/retry-ocr</p>
        <p class="text-sm text-gray-600">对指定图片重新进行OCR文字识别</p>
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

