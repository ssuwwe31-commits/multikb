<template>
  <div class="api-qa">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">问答API</h1>
      <p class="text-xl text-gray-600">文本问答、图片问答、流式输出等接口</p>
    </div>

    <section class="mb-16">
      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">/api/v1/qa</code>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">💬</div>
        <h2 class="text-3xl font-bold text-gray-900">问答接口</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">文本问答</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/qa/sessions/{session_id}/multimodal-questions</p>
          <p class="text-sm text-gray-600 mb-3">提交文本问题，获取AI回答</p>
          <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto mb-3">
            <code>{
  "question": "什么是知识库？",
  "search_type": "hybrid",
  "top_k": 5
}</code>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">图片问答</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/qa/sessions/{session_id}/image-search</p>
          <p class="text-sm text-gray-600 mb-3">上传图片进行问答</p>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">流式问答</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">WebSocket /api/v1/qa/sessions/{session_id}/stream</p>
          <p class="text-sm text-gray-600 mb-3">实时流式输出问答结果</p>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">📋</div>
        <h2 class="text-3xl font-bold text-gray-900">会话管理</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">创建会话</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/qa/sessions</p>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">获取会话</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/qa/sessions/{session_id}</p>
        </div>
        <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">会话列表</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/qa/sessions</p>
        </div>
        <div class="bg-gradient-to-br from-red-50 to-pink-50 rounded-xl p-6 border-2 border-red-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">删除会话</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">DELETE /api/v1/qa/sessions/{session_id}</p>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-overview" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">API概览 →</router-link>
        <router-link to="/docs/api-websocket" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">WebSocket API →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

