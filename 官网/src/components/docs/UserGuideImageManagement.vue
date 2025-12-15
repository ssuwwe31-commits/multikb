<template>
  <div class="user-guide-image-management">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">图片管理</h1>
      <p class="text-xl text-gray-600">图片上传、OCR识别、图片搜索等功能</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">📤</div>
        <h2 class="text-3xl font-bold text-gray-900">图片上传</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
          <li>进入图片管理页面</li>
          <li>点击"上传图片"按钮</li>
          <li>选择图片文件（支持JPG、PNG、GIF等格式）</li>
          <li>系统会自动进行：
            <ul class="list-disc list-inside ml-6 mt-2">
              <li>OCR文字识别（使用Qwen VL模型）</li>
              <li>图片向量化（使用CLIP模型）</li>
              <li>存储到MinIO</li>
            </ul>
          </li>
        </ol>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">图片搜索</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">以图搜图</h3>
          <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>上传一张图片</li>
            <li>系统使用CLIP模型提取图片特征</li>
            <li>在知识库中搜索相似图片</li>
            <li>返回相似度排序的结果</li>
          </ol>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">文本搜图</h3>
          <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>输入文本描述</li>
            <li>系统将文本转换为向量</li>
            <li>在图片向量库中搜索匹配</li>
            <li>返回相关图片</li>
          </ol>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">📝</div>
        <h2 class="text-3xl font-bold text-gray-900">OCR识别</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">自动OCR</h3>
            <p class="text-sm text-gray-700">图片上传后自动进行OCR识别，提取文字内容</p>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">重新OCR</h3>
            <p class="text-sm text-gray-700">如果OCR结果不准确，可以重新进行OCR识别</p>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">OCR结果查看</h3>
            <p class="text-sm text-gray-700">在图片详情页可以查看OCR识别的文字内容</p>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-image" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">图片API →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

