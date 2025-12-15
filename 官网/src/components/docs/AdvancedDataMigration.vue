<template>
  <div class="advanced-data-migration">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">数据迁移</h1>
      <p class="text-xl text-gray-600">数据导入导出、版本升级、数据迁移</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">📤</div>
        <h2 class="text-3xl font-bold text-gray-900">数据导出</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">导出知识库</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>导出知识库的所有文档和元数据</li>
              <li>支持JSON格式导出</li>
              <li>包含文档内容、分块、向量信息</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">导出文档</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>单个或批量导出文档</li>
              <li>保留文档的版本历史</li>
              <li>导出原始文件</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">📥</div>
        <h2 class="text-3xl font-bold text-gray-900">数据导入</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">导入知识库</h3>
            <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>准备导出文件（JSON格式）</li>
              <li>选择目标知识库或创建新知识库</li>
              <li>上传导入文件</li>
              <li>系统自动解析并导入数据</li>
            </ol>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">导入注意事项</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>确保版本兼容性</li>
              <li>检查数据完整性</li>
              <li>导入后验证数据</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔄</div>
        <h2 class="text-3xl font-bold text-gray-900">版本升级</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">升级步骤</h3>
            <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>备份当前数据</li>
              <li>查看升级说明和变更日志</li>
              <li>执行数据库迁移脚本</li>
              <li>更新应用代码</li>
              <li>验证升级结果</li>
            </ol>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">回滚方案</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>保留数据备份</li>
              <li>准备回滚脚本</li>
              <li>测试回滚流程</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">🚚</div>
        <h2 class="text-3xl font-bold text-gray-900">数据迁移</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">迁移场景</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>从其他系统迁移到Knowledge Base</li>
              <li>在不同环境间迁移数据</li>
              <li>合并多个知识库</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">迁移工具</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>使用API进行程序化迁移</li>
              <li>使用导出/导入功能</li>
              <li>使用迁移脚本</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/document-management" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">文档管理 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

