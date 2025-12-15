<template>
  <div class="api-websocket">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">WebSocket API</h1>
      <p class="text-xl text-gray-600">实时问答、任务进度、消息推送等WebSocket接口</p>
    </div>

    <section class="mb-16">
      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">ws://localhost:8000/ws</code>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔌</div>
        <h2 class="text-3xl font-bold text-gray-900">WebSocket连接</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">用户连接</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">WebSocket /ws/{user_id}</p>
          <p class="text-sm text-gray-600 mb-3">建立用户级别的WebSocket连接，接收实时消息</p>
          <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto">
            <code>const ws = new WebSocket('ws://localhost:8000/ws/123');</code>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">文档状态推送</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">WebSocket /ws/documents/status</p>
          <p class="text-sm text-gray-600 mb-3">实时推送文档处理状态更新</p>
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
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">📨</div>
        <h2 class="text-3xl font-bold text-gray-900">消息格式</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">消息类型</h3>
        <div class="space-y-3">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">文档状态更新</h4>
            <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto"><code>{
  "type": "document_status",
  "document_id": 123,
  "status": "processing",
  "progress": 50
}</code></pre>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">问答流式输出</h4>
            <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto"><code>{
  "type": "qa_stream",
  "chunk": "这是回答的一部分",
  "done": false
}</code></pre>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-overview" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">API概览 →</router-link>
        <router-link to="/docs/api-qa" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">问答API →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

