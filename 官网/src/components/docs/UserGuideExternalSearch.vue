<template>
  <div class="user-guide-external-search">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">联网搜索</h1>
      <p class="text-xl text-gray-600">SearxNG集成配置和联网搜索使用</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🌐</div>
        <h2 class="text-3xl font-bold text-gray-900">功能说明</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <p class="text-gray-700 mb-4">联网搜索功能可以在知识库无法回答问题时，自动从互联网搜索相关信息，扩展知识获取范围。</p>
        <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
          <li><strong>智能触发</strong>：当知识库检索结果不足时，自动触发联网搜索</li>
          <li><strong>结果摘要</strong>：对搜索结果进行智能摘要，提取关键信息</li>
          <li><strong>缓存机制</strong>：对搜索结果进行缓存，提升响应速度</li>
        </ul>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">⚙️</div>
        <h2 class="text-3xl font-bold text-gray-900">SearxNG配置</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">安装SearxNG</h3>
            <p class="text-sm text-gray-700 mb-2">使用Docker部署SearxNG：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">docker run -d -p 8080:8080 searxng/searxng</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">配置环境变量</h3>
            <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">
              <code>EXTERNAL_SEARCH_ENABLED=true<br>SEARXNG_URL=http://localhost:8080</code>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">💡</div>
        <h2 class="text-3xl font-bold text-gray-900">使用场景</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
          <li>知识库中没有相关信息时</li>
          <li>需要获取最新信息时</li>
          <li>查询实时数据时</li>
          <li>补充知识库内容时</li>
        </ul>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/knowledge-qa" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">知识问答 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

