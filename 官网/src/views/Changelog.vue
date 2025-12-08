<template>
  <div class="changelog-page">
    <Navbar />
    
    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto">
          <h1 class="text-5xl md:text-6xl font-bold mb-6">
            <span class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
              更新日志
            </span>
          </h1>
          <p class="text-xl text-gray-600 dark:text-gray-300">
            了解 Knowledge Base 的最新功能和改进
          </p>
        </div>
      </div>
    </section>

    <!-- Changelog Content -->
    <section class="py-20 bg-white dark:bg-gray-900">
      <div class="max-w-4xl mx-auto px-6 lg:px-8">
        <div class="space-y-12">
          <!-- Version 1.0.0 -->
          <div class="relative">
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full"></div>
            <div class="ml-8">
              <div class="flex items-center space-x-4 mb-4">
                <span class="px-4 py-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full text-sm font-semibold">
                  v1.0.0
                </span>
                <span class="text-gray-500 dark:text-gray-400 text-sm">2025年1月</span>
              </div>
              <h2 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-6">首次发布</h2>
              
              <div class="space-y-6">
                <!-- New Features -->
                <div>
                  <h3 class="text-xl font-semibold text-green-600 dark:text-green-400 mb-3 flex items-center">
                    <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    新功能
                  </h3>
                  <ul class="space-y-2 text-gray-700 dark:text-gray-300">
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>支持9种文档格式（PDF、DOCX、TXT、MD、HTML、XLSX、PPTX、CSV、LOG）</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>集成ClamAV安全扫描，防止恶意文件上传</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>多模态能力：支持文本、图片和混合输入</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>6种检索策略：向量检索、关键词检索、混合检索、重排序、语义检索、多模态检索</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>完整的RAG（检索增强生成）流程</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>文档版本管理和历史记录</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>用户权限管理和数据隔离</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>RESTful API和WebSocket实时通信</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>OpenAPI规范文档</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-green-500 mr-2">•</span>
                      <span>Kubernetes集群监控和诊断</span>
                    </li>
                  </ul>
                </div>

                <!-- Improvements -->
                <div>
                  <h3 class="text-xl font-semibold text-blue-600 dark:text-blue-400 mb-3 flex items-center">
                    <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd"/>
                    </svg>
                    改进
                  </h3>
                  <ul class="space-y-2 text-gray-700 dark:text-gray-300">
                    <li class="flex items-start">
                      <span class="text-blue-500 mr-2">•</span>
                      <span>优化文档解析和分块算法，提升检索准确性</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-blue-500 mr-2">•</span>
                      <span>改进向量检索性能，支持大规模文档库</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-blue-500 mr-2">•</span>
                      <span>增强多模态检索能力，支持图片语义检索</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-blue-500 mr-2">•</span>
                      <span>优化API响应时间，提升用户体验</span>
                    </li>
                  </ul>
                </div>

                <!-- Technical -->
                <div>
                  <h3 class="text-xl font-semibold text-purple-600 dark:text-purple-400 mb-3 flex items-center">
                    <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
                      <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    技术架构
                  </h3>
                  <ul class="space-y-2 text-gray-700 dark:text-gray-300">
                    <li class="flex items-start">
                      <span class="text-purple-500 mr-2">•</span>
                      <span>后端：FastAPI + SQLAlchemy + Celery</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-purple-500 mr-2">•</span>
                      <span>前端：Vue 3 + TypeScript + Element Plus</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-purple-500 mr-2">•</span>
                      <span>数据库：MySQL + OpenSearch + Redis</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-purple-500 mr-2">•</span>
                      <span>存储：MinIO对象存储</span>
                    </li>
                    <li class="flex items-start">
                      <span class="text-purple-500 mr-2">•</span>
                      <span>AI模型：Ollama + CLIP + Qwen VL + Rerank</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- Future Plans -->
          <div class="mt-16 p-8 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-2 border-blue-100 dark:border-blue-800">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">未来计划</h2>
            <ul class="space-y-3 text-gray-700 dark:text-gray-300">
              <li class="flex items-start">
                <span class="text-blue-500 mr-2">•</span>
                <span>知识图谱功能（企业版）</span>
              </li>
              <li class="flex items-start">
                <span class="text-blue-500 mr-2">•</span>
                <span>AI Agent智能助手（企业版）</span>
              </li>
              <li class="flex items-start">
                <span class="text-blue-500 mr-2">•</span>
                <span>更多文档格式支持</span>
              </li>
              <li class="flex items-start">
                <span class="text-blue-500 mr-2">•</span>
                <span>移动端应用</span>
              </li>
              <li class="flex items-start">
                <span class="text-blue-500 mr-2">•</span>
                <span>更多集成和插件</span>
              </li>
            </ul>
          </div>

          <!-- GitHub Link -->
          <div class="text-center pt-8">
            <p class="text-gray-600 dark:text-gray-400 mb-4">
              查看完整的更新历史和源代码
            </p>
            <a 
              href="https://github.com" 
              target="_blank"
              class="inline-flex items-center space-x-2 px-6 py-3 bg-gray-900 dark:bg-gray-800 text-white rounded-lg font-semibold hover:bg-gray-800 dark:hover:bg-gray-700 transition-all duration-300"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              <span>查看 GitHub</span>
            </a>
          </div>
        </div>
      </div>
    </section>
    
    <Footer />
  </div>
</template>

<script setup lang="ts">
import Navbar from '../components/layout/Navbar.vue'
import Footer from '../components/layout/Footer.vue'
</script>

<style scoped>
.changelog-page {
  min-height: 100vh;
}
</style>

