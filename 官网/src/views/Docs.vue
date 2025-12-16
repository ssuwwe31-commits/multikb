<template>
  <div class="docs-page">
    <Navbar />
    
    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto">
          <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 mb-6">
            <span class="text-sm font-medium text-blue-700 dark:text-blue-300">文档中心</span>
          </div>
          <h1 class="text-5xl md:text-6xl font-bold mb-6">
            <span class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
              文档
            </span>
          </h1>
          <p class="text-xl text-gray-600 dark:text-gray-300">
            完整的使用文档和API参考，帮助您快速上手和深入使用
          </p>
        </div>
      </div>
    </section>

    <!-- Documentation Categories -->
    <section class="py-20 bg-white dark:bg-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <!-- Getting Started -->
        <div class="mb-16">
          <div class="flex items-center space-x-4 mb-8">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <span class="text-2xl">🚀</span>
            </div>
            <h2 class="text-3xl font-bold text-gray-900 dark:text-gray-100">快速开始</h2>
          </div>
          
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <router-link 
              v-for="doc in gettingStartedDocs" 
              :key="doc.title"
              :to="doc.link"
              class="group p-6 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-2 border-green-100 dark:border-green-800 hover:border-green-300 dark:hover:border-green-700 hover:shadow-lg transition-all duration-300 cursor-pointer block"
            >
              <div class="flex items-center space-x-3 mb-4">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white">
                  {{ doc.icon }}
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ doc.title }}</h3>
              </div>
              <p class="text-gray-600 dark:text-gray-300 mb-4">{{ doc.description }}</p>
              <div class="flex items-center text-green-600 font-medium text-sm group-hover:translate-x-2 transition-transform">
                <span>查看文档</span>
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </router-link>
          </div>
        </div>

        <!-- Installation & Deployment -->
        <div class="mb-16">
          <div class="flex items-center space-x-4 mb-8">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span class="text-2xl">⚙️</span>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">安装部署</h2>
          </div>
          
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <router-link 
              v-for="doc in installationDocs" 
              :key="doc.title"
              :to="doc.link || '#'"
              class="group p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100 hover:border-blue-300 hover:shadow-lg transition-all duration-300 cursor-pointer block"
            >
              <div class="flex items-center space-x-3 mb-4">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white">
                  {{ doc.icon }}
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ doc.title }}</h3>
              </div>
              <p class="text-gray-600 dark:text-gray-300 mb-4">{{ doc.description }}</p>
              <div class="flex items-center text-blue-600 font-medium text-sm group-hover:translate-x-2 transition-transform">
                <span>查看文档</span>
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </router-link>
          </div>
        </div>

        <!-- User Guide -->
        <div class="mb-16">
          <div class="flex items-center space-x-4 mb-8">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
              <span class="text-2xl">📖</span>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">用户指南</h2>
          </div>
          
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <router-link 
              v-for="doc in userGuideDocs" 
              :key="doc.title"
              :to="doc.link || '#'"
              class="group p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-100 hover:border-purple-300 hover:shadow-lg transition-all duration-300 cursor-pointer block"
            >
              <div class="flex items-center space-x-3 mb-4">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white">
                  {{ doc.icon }}
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ doc.title }}</h3>
              </div>
              <p class="text-gray-600 dark:text-gray-300 mb-4">{{ doc.description }}</p>
              <div class="flex items-center text-purple-600 font-medium text-sm group-hover:translate-x-2 transition-transform">
                <span>查看文档</span>
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </router-link>
          </div>
        </div>

        <!-- API Documentation -->
        <div class="mb-16">
          <div class="flex items-center space-x-4 mb-8">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center">
              <span class="text-2xl">🔌</span>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">API文档</h2>
          </div>
          
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <router-link 
              v-for="doc in apiDocs" 
              :key="doc.title"
              :to="doc.link || '#'"
              class="group p-6 rounded-xl bg-gradient-to-br from-orange-50 to-red-50 border-2 border-orange-100 hover:border-orange-300 hover:shadow-lg transition-all duration-300 cursor-pointer block"
            >
              <div class="flex items-center space-x-3 mb-4">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white">
                  {{ doc.icon }}
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ doc.title }}</h3>
              </div>
              <p class="text-gray-600 dark:text-gray-300 mb-4">{{ doc.description }}</p>
              <div class="flex items-center text-orange-600 font-medium text-sm group-hover:translate-x-2 transition-transform">
                <span>查看文档</span>
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </router-link>
          </div>
        </div>

        <!-- Advanced Topics -->
        <div class="mb-16">
          <div class="flex items-center space-x-4 mb-8">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <span class="text-2xl">🎯</span>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">高级主题</h2>
          </div>
          
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <router-link 
              v-for="doc in advancedDocs" 
              :key="doc.title"
              :to="doc.link || '#'"
              class="group p-6 rounded-xl bg-gradient-to-br from-cyan-50 to-blue-50 border-2 border-cyan-100 hover:border-cyan-300 hover:shadow-lg transition-all duration-300 cursor-pointer block"
            >
              <div class="flex items-center space-x-3 mb-4">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white">
                  {{ doc.icon }}
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ doc.title }}</h3>
              </div>
              <p class="text-gray-600 dark:text-gray-300 mb-4">{{ doc.description }}</p>
              <div class="flex items-center text-cyan-600 font-medium text-sm group-hover:translate-x-2 transition-transform">
                <span>查看文档</span>
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </router-link>
          </div>
        </div>

        <!-- Troubleshooting -->
        <div class="mb-16">
          <div class="flex items-center space-x-4 mb-8">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center">
              <span class="text-2xl">🔧</span>
            </div>
            <h2 class="text-3xl font-bold text-gray-900">故障排除</h2>
          </div>
          
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <router-link 
              v-for="doc in troubleshootingDocs" 
              :key="doc.title"
              :to="doc.link || '#'"
              class="group p-6 rounded-xl bg-gradient-to-br from-yellow-50 to-orange-50 border-2 border-yellow-100 hover:border-yellow-300 hover:shadow-lg transition-all duration-300 cursor-pointer block"
            >
              <div class="flex items-center space-x-3 mb-4">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white">
                  {{ doc.icon }}
                </div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ doc.title }}</h3>
              </div>
              <p class="text-gray-600 dark:text-gray-300 mb-4">{{ doc.description }}</p>
              <div class="flex items-center text-yellow-600 font-medium text-sm group-hover:translate-x-2 transition-transform">
                <span>查看文档</span>
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-20 bg-gradient-to-br from-blue-600 to-purple-600 text-white">
      <div class="max-w-4xl mx-auto px-6 lg:px-8 text-center">
        <h2 class="text-4xl md:text-5xl font-bold mb-6">
          需要帮助？
        </h2>
        <p class="text-xl text-blue-100 mb-8">
          如果文档无法解决您的问题，我们的团队随时为您提供支持
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <router-link 
            to="/contact"
            class="px-8 py-4 bg-white text-blue-600 rounded-xl font-semibold hover:bg-gray-50 transition-all duration-300 hover:shadow-lg"
          >
            联系我们
          </router-link>
          <a 
            href="https://github.com/ssuwwe31-commits/multikb" 
            target="_blank"
            class="px-8 py-4 bg-transparent border-2 border-white text-white rounded-xl font-semibold hover:bg-white/10 transition-all duration-300"
          >
            GitHub Issues
          </a>
        </div>
      </div>
    </section>

    <Footer />
  </div>
</template>

<script setup lang="ts">
import Navbar from '../components/layout/Navbar.vue'
import Footer from '../components/layout/Footer.vue'

// 快速开始
const gettingStartedDocs = [
  {
    icon: '⚡',
    title: '5分钟快速开始',
    description: '5分钟快速上手 Multikb Base，体验核心功能',
    link: '/docs/getting-started'
  },
  {
    icon: '🎯',
    title: '核心概念',
    description: '了解知识库、文档、块、向量等核心概念',
    link: '/docs/core-concepts'
  },
  {
    icon: '📋',
    title: '系统要求',
    description: '查看系统要求、依赖服务和环境配置',
    link: '/docs/system-requirements'
  }
]

// 安装部署
const installationDocs = [
  {
    icon: '🐳',
    title: 'Docker部署',
    description: '使用Docker Compose一键部署，最简单的方式',
    link: '/docs/docker-deployment'
  },
  {
    icon: '☸️',
    title: 'Kubernetes部署',
    description: '在K8s集群中部署，适合生产环境',
    link: '/docs/kubernetes-deployment'
  },
  {
    icon: '💻',
    title: '源码部署',
    description: '从源码编译部署，完全自定义配置',
    link: '/docs/source-deployment'
  },
  {
    icon: '🔧',
    title: '环境配置',
    description: 'MySQL、OpenSearch、Redis、MinIO等中间件配置',
    link: '/docs/environment-config'
  },
  {
    icon: '🔐',
    title: '安全配置',
    description: 'SSL证书、防火墙、访问控制等安全配置',
    link: '/docs/security-config'
  },
  {
    icon: '📊',
    title: '监控告警',
    description: 'Prometheus、Grafana监控配置和告警设置',
    link: '/docs/monitoring-alerting'
  }
]

// 用户指南
const userGuideDocs = [
  {
    icon: '📄',
    title: '文档管理',
    description: '文档上传、解析、编辑、删除等操作指南',
    link: '/docs/document-management'
  },
  {
    icon: '💬',
    title: '知识问答',
    description: '如何使用多模态问答功能，提升问答效果',
    link: '/docs/knowledge-qa'
  },
  {
    icon: '🔍',
    title: '搜索功能',
    description: '六种检索策略的使用场景和最佳实践',
    link: '/docs/search-features'
  },
  {
    icon: '🖼️',
    title: '图片管理',
    description: '图片上传、OCR识别、图片搜索等功能',
    link: '/docs/image-management'
  },
  {
    icon: '📊',
    title: '版本管理',
    description: '文档级和块级版本管理，版本恢复和对比',
    link: '/docs/version-management'
  },
  {
    icon: '👥',
    title: '用户权限',
    description: '用户管理、角色权限、数据隔离配置',
    link: '/docs/user-permissions'
  },
  {
    icon: '🔒',
    title: '安全扫描',
    description: 'ClamAV病毒扫描配置和使用指南',
    link: '/docs/security-scanning'
  },
  {
    icon: '🌐',
    title: '联网搜索',
    description: 'SearxNG集成配置和联网搜索使用',
    link: '/docs/external-search'
  },
  {
    icon: '⚙️',
    title: '系统配置',
    description: '系统参数配置、模型切换、性能调优',
    link: '/docs/system-config'
  }
]

// API文档
const apiDocs = [
  {
    icon: '📡',
    title: 'API概览',
    description: '91个API接口概览，认证方式和请求格式',
    link: '/docs/api-overview'
  },
  {
    icon: '📚',
    title: '文档管理API',
    description: '文档上传、查询、更新、删除等接口文档',
    link: '/docs/api-document'
  },
  {
    icon: '💬',
    title: '问答API',
    description: '文本问答、图片问答、流式输出等接口',
    link: '/docs/api-qa'
  },
  {
    icon: '🔍',
    title: '搜索API',
    description: '文本搜索、向量搜索、混合搜索等接口',
    link: '/docs/api-search'
  },
  {
    icon: '🖼️',
    title: '图片API',
    description: '图片上传、OCR识别、图片搜索等接口',
    link: '/docs/api-image'
  },
  {
    icon: '📊',
    title: '管理API',
    description: '知识库管理、用户管理、系统配置等接口',
    link: '/docs/api-management'
  },
  {
    icon: '🔌',
    title: 'WebSocket API',
    description: '实时问答、任务进度、消息推送等WebSocket接口',
    link: '/docs/api-websocket'
  },
  {
    icon: '📖',
    title: 'OpenAPI规范',
    description: '完整的OpenAPI 3.0规范文档，支持代码生成',
    link: '/docs/api-openapi'
  }
]

// 高级主题
const advancedDocs = [
  {
    icon: '🎨',
    title: '多模态配置',
    description: 'Qwen VL、CLIP模型配置和优化',
    link: '/docs/multimodal-config'
  },
  {
    icon: '🔍',
    title: '检索优化',
    description: '向量检索、Rerank模型调优和性能优化',
    link: '/docs/retrieval-optimization'
  },
  {
    icon: '📊',
    title: '知识图谱',
    description: '知识图谱构建、实体提取、关系识别（企业版）',
    link: '/docs/knowledge-graph'
  },
  {
    icon: '🤖',
    title: '智能Agent',
    description: '智能Agent配置和使用（企业版）',
    link: '/docs/ai-agent'
  },
  {
    icon: '☸️',
    title: 'K8s监控',
    description: 'K8s集群监控和自动诊断（企业版）',
    link: '/docs/k8s-monitoring'
  },
  {
    icon: '🔄',
    title: '数据迁移',
    description: '数据导入导出、版本升级、数据迁移',
    link: '/docs/data-migration'
  },
  {
    icon: '⚡',
    title: '性能优化',
    description: '系统性能优化、缓存策略、并发调优',
    link: '/docs/performance-optimization'
  },
  {
    icon: '🔐',
    title: '安全加固',
    description: '安全最佳实践、漏洞防护、合规配置',
    link: '/docs/security-hardening'
  },
  {
    icon: '🔌',
    title: '二次开发',
    description: '插件开发、API扩展、自定义功能开发',
    link: '/docs/custom-development'
  }
]

// 故障排除
// 故障排除
const troubleshootingDocs = [
  {
    icon: '❓',
    title: '常见问题',
    description: '安装、配置、使用中的常见问题和解决方案',
    link: '/docs/faq'
  },
  {
    icon: '🐛',
    title: '错误排查',
    description: '常见错误代码、错误原因和解决方法',
    link: '/docs/error-troubleshooting'
  },
  {
    icon: '📝',
    title: '日志分析',
    description: '日志查看、日志分析、问题定位方法',
    link: '/docs/log-analysis'
  },
  {
    icon: '🔧',
    title: '性能问题',
    description: '性能问题诊断和优化方法',
    link: '/docs/performance-issues'
  },
  {
    icon: '🔒',
    title: '安全问题',
    description: '安全相关问题排查和解决方案',
    link: '/docs/security-issues'
  },
  {
    icon: '💬',
    title: '社区支持',
    description: 'GitHub Issues、社区论坛、技术支持',
    link: '/docs/community-support'
  }
]
</script>

<style scoped>
.docs-page {
  min-height: 100vh;
}
</style>
