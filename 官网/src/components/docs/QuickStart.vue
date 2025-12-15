<template>
  <div class="quick-start">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
        5分钟快速开始
      </h1>
      <p class="text-xl text-gray-600">
        快速上手 Knowledge Base，体验核心功能
      </p>
    </div>

    <!-- Prerequisites -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-xl">
          ✅
        </div>
        <h2 class="text-3xl font-bold text-gray-900">前置准备</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
        <p class="text-gray-700 mb-4">在开始之前，请确保您已经：</p>
        <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
          <li>完成系统部署（Docker、K8s或源码部署）</li>
          <li>访问系统地址（通常是 <code class="bg-gray-200 px-1 rounded">http://localhost:3000</code>）</li>
          <li>准备好一个测试文档（PDF、DOCX、TXT等格式）</li>
        </ul>
      </div>
    </section>

    <!-- Step 1: Login -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold">
          1
        </div>
        <h2 class="text-3xl font-bold text-gray-900">登录系统</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <p class="text-gray-700 mb-3">打开浏览器，访问系统地址，使用您的账号登录。</p>
            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p class="text-sm text-yellow-800">
                <strong>提示：</strong>如果是首次使用，可能需要注册账号或使用管理员提供的账号。
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Step 2: Create Knowledge Base -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-2xl font-bold">
          2
        </div>
        <h2 class="text-3xl font-bold text-gray-900">创建知识库</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>点击"创建知识库"按钮</li>
            <li>填写知识库名称（例如："测试知识库"）</li>
            <li>填写描述（可选）</li>
            <li>点击"确定"创建</li>
          </ol>
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
            <p class="text-sm text-blue-800">
              <strong>说明：</strong>知识库是组织和管理文档的基本单元，每个知识库的数据相互隔离。
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Step 3: Upload Document -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-2xl font-bold">
          3
        </div>
        <h2 class="text-3xl font-bold text-gray-900">上传文档</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-4">
          <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>进入刚创建的知识库</li>
            <li>点击"上传文档"按钮</li>
            <li>选择您的测试文档（支持PDF、DOCX、TXT等格式）</li>
            <li>等待文档处理完成（系统会自动进行解析、分块、向量化）</li>
          </ol>
          <div class="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
            <p class="text-sm text-green-800">
              <strong>提示：</strong>文档处理时间取决于文档大小，通常几秒到几分钟不等。您可以在文档列表中查看处理状态。
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Step 4: Ask Questions -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center text-white text-2xl font-bold">
          4
        </div>
        <h2 class="text-3xl font-bold text-gray-900">开始问答</h2>
      </div>

      <div class="bg-gradient-to-br from-teal-50 to-cyan-50 rounded-xl p-6 border-2 border-teal-100">
        <div class="space-y-4">
          <ol class="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>等待文档处理完成后，进入"知识问答"页面</li>
            <li>在输入框中输入您的问题（例如："文档的主要内容是什么？"）</li>
            <li>点击"发送"或按Enter键</li>
            <li>系统会自动检索相关知识并生成回答</li>
          </ol>
          <div class="grid md:grid-cols-2 gap-4 mt-4">
            <div class="bg-white p-4 rounded-lg border border-gray-200">
              <h4 class="font-semibold text-gray-900 mb-2">💡 试试这些问题：</h4>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li>"文档的核心内容是什么？"</li>
                <li>"请总结一下文档的要点"</li>
                <li>"文档中提到了哪些关键概念？"</li>
              </ul>
            </div>
            <div class="bg-white p-4 rounded-lg border border-gray-200">
              <h4 class="font-semibold text-gray-900 mb-2">✨ 核心功能：</h4>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li>智能语义检索</li>
                <li>多模态问答</li>
                <li>引用溯源</li>
                <li>流式输出</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Step 5: Explore More -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
          5
        </div>
        <h2 class="text-3xl font-bold text-gray-900">探索更多功能</h2>
      </div>

      <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
        <div class="grid md:grid-cols-3 gap-4">
          <div class="bg-white p-5 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
            <div class="text-3xl mb-3">🔍</div>
            <h4 class="font-semibold text-gray-900 mb-2">搜索功能</h4>
            <p class="text-sm text-gray-700">尝试使用搜索功能，体验六种检索策略</p>
          </div>
          <div class="bg-white p-5 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
            <div class="text-3xl mb-3">🖼️</div>
            <h4 class="font-semibold text-gray-900 mb-2">图片管理</h4>
            <p class="text-sm text-gray-700">上传图片，体验OCR识别和图片搜索</p>
          </div>
          <div class="bg-white p-5 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
            <div class="text-3xl mb-3">📊</div>
            <h4 class="font-semibold text-gray-900 mb-2">版本管理</h4>
            <p class="text-sm text-gray-700">查看文档版本历史，体验版本恢复功能</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Next Steps -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">
          🚀
        </div>
        <h2 class="text-3xl font-bold text-gray-900">下一步</h2>
      </div>

      <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
        <p class="text-gray-700 mb-4">恭喜！您已经完成了快速开始。接下来可以：</p>
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">📖 深入学习</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>阅读<router-link to="/docs/core-concepts" class="text-blue-600 hover:underline">核心概念</router-link>文档</li>
              <li>查看<router-link to="/docs/document-management" class="text-blue-600 hover:underline">文档管理</router-link>指南</li>
              <li>学习<router-link to="/docs/knowledge-qa" class="text-blue-600 hover:underline">知识问答</router-link>功能</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">⚙️ 系统配置</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>配置<router-link to="/docs/system-config" class="text-blue-600 hover:underline">系统参数</router-link></li>
              <li>优化<router-link to="/docs/retrieval-optimization" class="text-blue-600 hover:underline">检索性能</router-link></li>
              <li>设置<router-link to="/docs/security-config" class="text-blue-600 hover:underline">安全配置</router-link></li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Common Issues -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-pink-600 flex items-center justify-center text-white text-xl">
          ❓
        </div>
        <h2 class="text-3xl font-bold text-gray-900">常见问题</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-pink-50 rounded-xl p-6 border-2 border-red-100">
        <div class="space-y-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">Q: 文档上传后一直显示"处理中"？</h4>
            <p class="text-sm text-gray-700 ml-4">A: 请检查Celery Worker是否正常运行，查看日志了解具体错误信息。</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">Q: 问答时没有返回结果？</h4>
            <p class="text-sm text-gray-700 ml-4">A: 请确保文档已处理完成，并且Ollama服务正常运行。检查系统日志查看详细错误。</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">Q: 如何查看更详细的帮助？</h4>
            <p class="text-sm text-gray-700 ml-4">A: 请访问<router-link to="/docs" class="text-blue-600 hover:underline">文档中心</router-link>，或查看<router-link to="/docs/faq" class="text-blue-600 hover:underline">常见问题</router-link>页面。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/core-concepts" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          核心概念 →
        </router-link>
        <router-link to="/docs/document-management" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          文档管理 →
        </router-link>
        <router-link to="/docs/knowledge-qa" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
          知识问答 →
        </router-link>
        <router-link to="/docs/faq" class="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors">
          常见问题 →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

