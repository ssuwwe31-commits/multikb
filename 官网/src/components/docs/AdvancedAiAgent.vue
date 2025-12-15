<template>
  <div class="advanced-ai-agent">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">智能Agent</h1>
      <p class="text-xl text-gray-600">智能Agent配置和使用（企业版）</p>
    </div>

    <div class="mb-6 p-4 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
      <div class="flex items-start space-x-3">
        <svg class="w-6 h-6 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        <div>
          <div class="font-semibold text-yellow-900 mb-1">企业版功能</div>
          <div class="text-sm text-yellow-800">智能Agent功能仅在企业版中提供，需要企业版License。</div>
        </div>
      </div>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🤖</div>
        <h2 class="text-3xl font-bold text-gray-900">Agent概述</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <p class="text-gray-700 mb-4">智能Agent可以理解自然语言任务，自动分解为多个步骤并执行，支持工具调用和上下文记忆。</p>
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">核心能力</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>多步骤任务自动执行</li>
              <li>自然语言命令理解</li>
              <li>工具调用（搜索、创建、更新等）</li>
              <li>上下文记忆管理</li>
            </ul>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">任务类型</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>创建知识库</li>
              <li>上传文档</li>
              <li>管理成员</li>
              <li>搜索和分析</li>
              <li>自定义任务</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">⚙️</div>
        <h2 class="text-3xl font-bold text-gray-900">使用方式</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">创建任务</h3>
            <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>使用自然语言描述任务</li>
              <li>Agent自动理解意图并分解步骤</li>
              <li>系统开始执行任务</li>
            </ol>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">任务执行</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>实时查看任务执行进度</li>
              <li>查看每个步骤的执行结果</li>
              <li>关键操作需要用户确认</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">任务管理</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>查看任务历史</li>
              <li>暂停和恢复任务</li>
              <li>查看任务执行详情</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🛠️</div>
        <h2 class="text-3xl font-bold text-gray-900">工具系统</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <p class="text-gray-700 mb-4">Agent可以使用以下工具执行任务：</p>
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">知识库工具</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>create_knowledge_base</li>
              <li>search_documents</li>
              <li>upload_document</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">用户工具</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>add_member</li>
              <li>remove_member</li>
              <li>update_permission</li>
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

