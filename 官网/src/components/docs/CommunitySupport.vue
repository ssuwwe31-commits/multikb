<template>
  <div class="community-support">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        社区支持
      </h1>
      <p class="text-xl text-gray-600">
        GitHub Issues、社区论坛、技术支持
      </p>
    </div>

    <!-- Support Channels -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          💬
        </div>
        <h2 class="text-3xl font-bold text-gray-900">支持渠道</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <div class="flex items-center space-x-3 mb-4">
            <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl">
              🐙
            </div>
            <h3 class="text-xl font-bold text-gray-900">GitHub Issues</h3>
          </div>
          <p class="text-gray-700 mb-4">
            报告Bug、提出功能建议、参与讨论
          </p>
          <ul class="space-y-2 text-sm text-gray-700 mb-4">
            <li>• 提交Bug报告</li>
            <li>• 功能请求</li>
            <li>• 技术讨论</li>
            <li>• 查看已知问题</li>
          </ul>
          <a 
            href="https://github.com" 
            target="_blank"
            class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            访问GitHub →
          </a>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <div class="flex items-center space-x-3 mb-4">
            <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-2xl">
              💬
            </div>
            <h3 class="text-xl font-bold text-gray-900">社区论坛</h3>
          </div>
          <p class="text-gray-700 mb-4">
            与其他用户交流经验、分享最佳实践
          </p>
          <ul class="space-y-2 text-sm text-gray-700 mb-4">
            <li>• 使用经验分享</li>
            <li>• 最佳实践讨论</li>
            <li>• 问题求助</li>
            <li>• 社区活动</li>
          </ul>
          <a 
            href="#" 
            class="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            访问论坛 →
          </a>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <div class="flex items-center space-x-3 mb-4">
            <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-2xl">
              📧
            </div>
            <h3 class="text-xl font-bold text-gray-900">邮件支持</h3>
          </div>
          <p class="text-gray-700 mb-4">
            发送邮件获取技术支持（企业用户）
          </p>
          <ul class="space-y-2 text-sm text-gray-700 mb-4">
            <li>• 技术支持</li>
            <li>• 商业咨询</li>
            <li>• 定制开发</li>
            <li>• 培训服务</li>
          </ul>
          <router-link 
            to="/contact"
            class="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            联系我们 →
          </router-link>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <div class="flex items-center space-x-3 mb-4">
            <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-2xl">
              📚
            </div>
            <h3 class="text-xl font-bold text-gray-900">文档中心</h3>
          </div>
          <p class="text-gray-700 mb-4">
            查阅完整的使用文档和API参考
          </p>
          <ul class="space-y-2 text-sm text-gray-700 mb-4">
            <li>• 快速开始指南</li>
            <li>• 用户手册</li>
            <li>• API文档</li>
            <li>• 故障排除</li>
          </ul>
          <router-link 
            to="/docs"
            class="inline-flex items-center px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
          >
            查看文档 →
          </router-link>
        </div>
      </div>
    </section>

    <!-- How to Get Help -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          ❓
        </div>
        <h2 class="text-3xl font-bold text-gray-900">如何获取帮助</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <ol class="space-y-4">
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">1</span>
            <div>
              <h3 class="font-semibold text-gray-900">查阅文档</h3>
              <p class="text-sm text-gray-700 mt-1">首先查看 <router-link to="/docs" class="text-blue-600 hover:underline">文档中心</router-link> 和 <router-link to="/docs/faq" class="text-blue-600 hover:underline">常见问题</router-link>，很多问题都有详细解答</p>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">2</span>
            <div>
              <h3 class="font-semibold text-gray-900">搜索已有问题</h3>
              <p class="text-sm text-gray-700 mt-1">在GitHub Issues中搜索类似问题，可能已经有人遇到并解决了</p>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">3</span>
            <div>
              <h3 class="font-semibold text-gray-900">提交问题</h3>
              <p class="text-sm text-gray-700 mt-1">如果问题仍未解决，在GitHub Issues中提交新问题，请提供：</p>
              <ul class="list-disc list-inside text-sm text-gray-700 mt-2 ml-4">
                <li>问题描述和复现步骤</li>
                <li>错误信息和日志</li>
                <li>系统环境信息</li>
                <li>相关配置信息</li>
              </ul>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">4</span>
            <div>
              <h3 class="font-semibold text-gray-900">参与讨论</h3>
              <p class="text-sm text-gray-700 mt-1">在社区论坛中与其他用户交流，分享经验和解决方案</p>
            </div>
          </li>
        </ol>
      </div>
    </section>

    <!-- Contributing -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
          🤝
        </div>
        <h2 class="text-3xl font-bold text-gray-900">参与贡献</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">代码贡献</h3>
          <ul class="space-y-2 text-gray-700">
            <li>• 提交Pull Request修复Bug</li>
            <li>• 实现新功能</li>
            <li>• 改进代码质量</li>
            <li>• 编写单元测试</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">文档贡献</h3>
          <ul class="space-y-2 text-gray-700">
            <li>• 完善使用文档</li>
            <li>• 翻译文档</li>
            <li>• 编写教程和示例</li>
            <li>• 修复文档错误</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">社区支持</h3>
          <ul class="space-y-2 text-gray-700">
            <li>• 回答其他用户的问题</li>
            <li>• 分享使用经验</li>
            <li>• 推广项目</li>
            <li>• 组织社区活动</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">反馈建议</h3>
          <ul class="space-y-2 text-gray-700">
            <li>• 报告Bug</li>
            <li>• 提出功能建议</li>
            <li>• 用户体验改进</li>
            <li>• 性能优化建议</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Community Guidelines -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📋
        </div>
        <h2 class="text-3xl font-bold text-gray-900">社区准则</h2>
      </div>

      <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
        <ul class="space-y-3">
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">尊重他人</strong>
              <p class="text-sm text-gray-700 mt-1">保持礼貌和尊重，避免使用攻击性语言</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">提供有用信息</strong>
              <p class="text-sm text-gray-700 mt-1">提问时提供足够的信息，帮助他人理解和解决问题</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">遵守开源协议</strong>
              <p class="text-sm text-gray-700 mt-1">遵守项目的开源协议，尊重知识产权</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">积极反馈</strong>
              <p class="text-sm text-gray-700 mt-1">及时反馈问题，帮助改进项目质量</p>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/faq" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          常见问题 →
        </router-link>
        <router-link to="/contact" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          联系我们 →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// No script logic needed for static content
</script>

<style scoped>
/* Add any specific styles for this document if needed */
</style>

