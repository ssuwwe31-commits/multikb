<template>
  <div class="user-guide-user-permissions">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">用户权限</h1>
      <p class="text-xl text-gray-600">用户管理、角色权限、数据隔离配置</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">👥</div>
        <h2 class="text-3xl font-bold text-gray-900">用户管理</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">用户列表</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>查看所有用户</li>
            <li>搜索和筛选用户</li>
            <li>查看用户详细信息</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">个人信息</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>修改个人资料</li>
            <li>更改密码</li>
            <li>邮箱验证</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔐</div>
        <h2 class="text-3xl font-bold text-gray-900">权限管理</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">知识库权限</h3>
            <p class="text-sm text-gray-700 mb-3">每个知识库可以设置不同的访问权限：</p>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li><strong>所有者</strong>：完全控制权限</li>
              <li><strong>编辑者</strong>：可以编辑文档和内容</li>
              <li><strong>查看者</strong>：只能查看，不能修改</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">成员管理</h3>
            <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>在知识库设置中添加成员</li>
              <li>为成员分配相应权限</li>
              <li>可以随时修改或移除成员</li>
            </ol>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔒</div>
        <h2 class="text-3xl font-bold text-gray-900">数据隔离</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">用户级隔离</h3>
            <p class="text-sm text-gray-700">每个用户的数据默认只能自己访问，确保数据安全</p>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">知识库级隔离</h3>
            <p class="text-sm text-gray-700">不同知识库之间的数据完全隔离，互不影响</p>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">共享机制</h3>
            <p class="text-sm text-gray-700">通过知识库成员管理实现数据共享，同时保持权限控制</p>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-management" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">管理API →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

