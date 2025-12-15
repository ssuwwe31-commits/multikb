<template>
  <div class="api-management">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">管理API</h1>
      <p class="text-xl text-gray-600">知识库管理、用户管理、系统配置等接口</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">📚</div>
        <h2 class="text-3xl font-bold text-gray-900">知识库管理</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-4">/api/v1/knowledge-bases</code>

        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">知识库操作</h4>
            <ul class="space-y-1 text-sm text-gray-700">
              <li>• GET /api/v1/knowledge-bases - 获取列表</li>
              <li>• POST /api/v1/knowledge-bases - 创建知识库</li>
              <li>• GET /api/v1/knowledge-bases/{kb_id} - 获取详情</li>
              <li>• PUT /api/v1/knowledge-bases/{kb_id} - 更新</li>
              <li>• DELETE /api/v1/knowledge-bases/{kb_id} - 删除</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">成员管理</h4>
            <ul class="space-y-1 text-sm text-gray-700">
              <li>• GET /api/v1/knowledge-bases/{kb_id}/members - 成员列表</li>
              <li>• POST /api/v1/knowledge-bases/{kb_id}/members - 添加成员</li>
              <li>• PUT /api/v1/knowledge-bases/{kb_id}/members/{user_id} - 更新权限</li>
              <li>• DELETE /api/v1/knowledge-bases/{kb_id}/members/{user_id} - 移除成员</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">👥</div>
        <h2 class="text-3xl font-bold text-gray-900">用户管理</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-4">/api/v1/users</code>

        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">用户信息</h4>
            <ul class="space-y-1 text-sm text-gray-700">
              <li>• PUT /api/v1/users/me - 更新个人信息</li>
              <li>• POST /api/v1/users/me/password - 修改密码</li>
              <li>• GET /api/v1/users/list - 用户列表（管理员）</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">邮箱验证</h4>
            <ul class="space-y-1 text-sm text-gray-700">
              <li>• POST /api/v1/users/me/email/verify - 发送验证邮件</li>
              <li>• POST /api/v1/users/me/email/confirm - 确认邮箱</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">📊</div>
        <h2 class="text-3xl font-bold text-gray-900">数据统计</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-4">/api/v1/statistics</code>

        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">统计接口</h4>
            <ul class="space-y-1 text-sm text-gray-700">
              <li>• GET /api/v1/statistics/personal - 个人统计</li>
              <li>• GET /api/v1/statistics/trends - 趋势统计</li>
              <li>• GET /api/v1/statistics/knowledge-bases/heatmap - 知识库热力图</li>
              <li>• GET /api/v1/statistics/search/hotwords - 搜索热词</li>
            </ul>
          </div>
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

