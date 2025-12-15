<template>
  <div class="user-guide-knowledge-qa">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">知识问答</h1>
      <p class="text-xl text-gray-600">如何使用多模态问答功能，提升问答效果</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">💬</div>
        <h2 class="text-3xl font-bold text-gray-900">问答方式</h2>
      </div>

      <div class="grid md:grid-cols-3 gap-6">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">文本问答</h3>
          <p class="text-sm text-gray-700 mb-3">直接输入文本问题，获取AI回答</p>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700">
            <li>支持自然语言提问</li>
            <li>自动检索相关知识</li>
            <li>提供引用来源</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">图片问答</h3>
          <p class="text-sm text-gray-700 mb-3">上传图片，AI识别图片内容并回答</p>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700">
            <li>OCR文字识别</li>
            <li>图片内容理解</li>
            <li>结合知识库回答</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">图文混合问答</h3>
          <p class="text-sm text-gray-700 mb-3">同时输入文本和图片</p>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700">
            <li>多模态理解</li>
            <li>综合信息回答</li>
            <li>更准确的答案</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">检索策略</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <p class="text-gray-700 mb-4">Knowledge Base 提供六种检索策略，系统会根据问题自动选择最佳策略：</p>
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">1. 向量检索</h4>
            <p class="text-sm text-gray-700">基于语义相似度，理解问题意图</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">2. 关键词检索</h4>
            <p class="text-sm text-gray-700">传统全文检索，快速定位关键词</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">3. 混合检索</h4>
            <p class="text-sm text-gray-700">结合向量和关键词优势</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">4. 精确检索</h4>
            <p class="text-sm text-gray-700">针对特定短语精确匹配</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">5. 模糊检索</h4>
            <p class="text-sm text-gray-700">处理错别字和不完整查询</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">6. 多模态检索</h4>
            <p class="text-sm text-gray-700">结合文本和图片信息</p>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">⚙️</div>
        <h2 class="text-3xl font-bold text-gray-900">会话管理</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">创建会话</h3>
            <p class="text-sm text-gray-700">每次问答都会在会话中进行，系统会记住上下文</p>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">会话历史</h3>
            <p class="text-sm text-gray-700">可以查看历史问答记录，继续之前的对话</p>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">切换知识库</h3>
            <p class="text-sm text-gray-700">可以在不同知识库之间切换，针对不同领域提问</p>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl">✨</div>
        <h2 class="text-3xl font-bold text-gray-900">提升问答效果</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
        <ul class="space-y-3">
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">明确的问题描述</strong>
              <p class="text-sm text-gray-700 mt-1">尽量详细地描述问题，提供必要的上下文信息</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">选择合适的知识库</strong>
              <p class="text-sm text-gray-700 mt-1">确保提问的知识库包含相关文档</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">查看引用来源</strong>
              <p class="text-sm text-gray-700 mt-1">答案中的引用可以帮助您验证答案的准确性</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">使用流式输出</strong>
              <p class="text-sm text-gray-700 mt-1">启用流式输出可以实时看到答案生成过程</p>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-qa" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">问答API →</router-link>
        <router-link to="/docs/search-features" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">搜索功能 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

