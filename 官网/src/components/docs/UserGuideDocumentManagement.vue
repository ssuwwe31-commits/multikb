<template>
  <div class="user-guide-document-management">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        文档管理
      </h1>
      <p class="text-xl text-gray-600">
        文档上传、解析、编辑、删除等操作指南
      </p>
    </div>

    <!-- Document Upload -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📤
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档上传</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">单文件上传</h3>
          <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>进入知识库页面，选择目标知识库</li>
            <li>点击"上传文档"按钮</li>
            <li>选择要上传的文件（支持PDF、DOCX、PPTX、Excel、HTML、MD、TXT、JSON、XML）</li>
            <li>填写文档信息（可选）：
              <ul class="list-disc list-inside ml-6 mt-2">
                <li>文档名称</li>
                <li>分类</li>
                <li>标签</li>
              </ul>
            </li>
            <li>点击"确定"开始上传</li>
          </ol>
          <div class="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p class="text-sm text-yellow-800"><strong>提示：</strong>文档上传后会自动进行解析、分块和向量化处理，处理时间取决于文档大小。</p>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">批量上传</h3>
          <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>点击"批量上传"按钮</li>
            <li>选择多个文件（支持拖拽）</li>
            <li>系统会自动为每个文件创建上传任务</li>
            <li>可以在任务列表中查看上传和处理进度</li>
          </ol>
        </div>
      </div>
    </section>

    <!-- Document Viewing -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          👁️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档查看</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">文档列表</h3>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>在知识库页面查看所有文档</li>
              <li>支持按状态、分类、标签筛选</li>
              <li>支持搜索文档名称</li>
              <li>可以按上传时间、修改时间排序</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">文档详情</h3>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>点击文档名称进入详情页</li>
              <li>查看文档基本信息（名称、大小、状态、上传时间等）</li>
              <li>查看文档分块列表</li>
              <li>查看文档预览内容</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">文档预览</h3>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>支持在线预览文档内容</li>
              <li>PDF、图片等格式可直接预览</li>
              <li>文本类文档显示格式化内容</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Document Editing -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">
          ✏️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档编辑</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">编辑文档信息</h3>
          <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>在文档详情页点击"编辑"按钮</li>
            <li>修改文档名称、分类、标签等信息</li>
            <li>保存更改</li>
          </ol>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">编辑文档内容（块级编辑）</h3>
          <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>在文档详情页查看分块列表</li>
            <li>点击要编辑的分块</li>
            <li>在编辑器中修改内容</li>
            <li>保存后系统会自动：
              <ul class="list-disc list-inside ml-6 mt-2">
                <li>重新向量化修改的内容</li>
                <li>更新OpenSearch索引</li>
                <li>创建新的版本记录</li>
              </ul>
            </li>
          </ol>
        </div>
      </div>
    </section>

    <!-- Document Organization -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📁
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档组织</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">分类管理</h3>
          <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>为文档设置分类，便于组织和管理</li>
            <li>支持多级分类结构</li>
            <li>可以按分类筛选文档</li>
            <li>支持批量修改分类</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">标签管理</h3>
          <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>为文档添加标签，便于检索</li>
            <li>支持多个标签</li>
            <li>可以按标签筛选文档</li>
            <li>支持批量添加、删除、替换标签</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Document Deletion -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-pink-600 flex items-center justify-center text-white text-xl">
          🗑️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档删除</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-pink-50 rounded-xl p-6 border-2 border-red-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">单个删除</h3>
            <ol class="list-decimal list-inside space-y-1 text-gray-700 ml-4">
              <li>在文档列表或详情页点击"删除"按钮</li>
              <li>确认删除操作</li>
              <li>系统会删除文档及其所有分块、向量数据</li>
            </ol>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">批量删除</h3>
            <ol class="list-decimal list-inside space-y-1 text-gray-700 ml-4">
              <li>在文档列表中勾选要删除的文档</li>
              <li>点击"批量删除"按钮</li>
              <li>确认删除操作</li>
            </ol>
          </div>
          <div class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p class="text-sm text-yellow-800"><strong>警告：</strong>删除操作不可恢复，请谨慎操作。删除文档会同时删除所有相关的分块、向量和版本记录。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Document Status -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">
          📊
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档状态</h2>
      </div>

      <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">处理中 (processing)</h3>
            <p class="text-sm text-gray-700">文档正在上传或处理中</p>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">已完成 (completed)</h3>
            <p class="text-sm text-gray-700">文档处理完成，可以正常使用</p>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">失败 (failed)</h3>
            <p class="text-sm text-gray-700">文档处理失败，可以查看错误信息并重新处理</p>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">已删除 (deleted)</h3>
            <p class="text-sm text-gray-700">文档已被删除（软删除）</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Best Practices -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-xl">
          ✅
        </div>
        <h2 class="text-3xl font-bold text-gray-900">最佳实践</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
        <ul class="space-y-3">
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">合理组织文档</strong>
              <p class="text-sm text-gray-700 mt-1">使用分类和标签对文档进行组织，便于后续查找和管理</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">及时处理失败文档</strong>
              <p class="text-sm text-gray-700 mt-1">定期检查处理失败的文档，查看错误信息并重新处理</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">使用批量操作</strong>
              <p class="text-sm text-gray-700 mt-1">对于大量文档，使用批量上传、批量移动、批量标签等功能提高效率</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">定期清理</strong>
              <p class="text-sm text-gray-700 mt-1">定期清理不需要的文档，保持知识库整洁</p>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/version-management" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          版本管理 →
        </router-link>
        <router-link to="/docs/api-document" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          文档管理API →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

