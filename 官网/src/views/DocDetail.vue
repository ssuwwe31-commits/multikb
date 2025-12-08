<template>
  <div class="doc-detail-page">
    <Navbar />
    
    <div class="max-w-5xl mx-auto px-6 lg:px-8 py-20">
      <!-- Breadcrumb & Back Button -->
      <div class="mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <nav>
          <div class="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
            <router-link to="/" class="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">首页</router-link>
            <span>/</span>
            <router-link to="/docs" class="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">文档</router-link>
            <span>/</span>
            <span class="text-gray-900 dark:text-gray-100 font-medium">{{ docTitle }}</span>
          </div>
        </nav>
        
        <router-link 
          to="/docs"
          class="group flex items-center space-x-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 border-2 border-blue-300 dark:border-blue-700 hover:border-blue-400 dark:hover:border-blue-600 hover:from-blue-100 hover:to-purple-100 dark:hover:from-blue-800/40 dark:hover:to-purple-800/40 text-blue-700 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-200 transition-all duration-300 shadow-md hover:shadow-lg animate-pulse-glow hover:animate-none relative overflow-hidden"
        >
          <!-- Animated background effect -->
          <div class="absolute inset-0 bg-gradient-to-r from-blue-400/20 to-purple-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          
          <!-- Arrow icon with animation -->
          <svg class="w-5 h-5 relative z-10 transform group-hover:-translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          
          <!-- Text with subtle animation -->
          <span class="font-medium relative z-10">返回文档列表</span>
          
          <!-- Pulsing dot indicator -->
          <span class="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></span>
          <span class="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></span>
        </router-link>
      </div>

      <!-- Document Content -->
      <article class="prose prose-lg dark:prose-invert max-w-none bg-white dark:bg-gray-800 rounded-2xl p-8 md:p-12 shadow-sm">
        <component :is="docComponent" />
      </article>
    </div>

    <Footer />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from '../components/layout/Navbar.vue'
import Footer from '../components/layout/Footer.vue'
import QuickStart from '../components/docs/QuickStart.vue'
import CoreConcepts from '../components/docs/CoreConcepts.vue'
import SystemRequirements from '../components/docs/SystemRequirements.vue'
import FAQ from '../components/docs/FAQ.vue'
import ErrorTroubleshooting from '../components/docs/ErrorTroubleshooting.vue'
import LogAnalysis from '../components/docs/LogAnalysis.vue'
import PerformanceIssues from '../components/docs/PerformanceIssues.vue'
import SecurityIssues from '../components/docs/SecurityIssues.vue'
import CommunitySupport from '../components/docs/CommunitySupport.vue'
import ApiOverview from '../components/docs/ApiOverview.vue'
import ApiDocument from '../components/docs/ApiDocument.vue'
import ApiQa from '../components/docs/ApiQa.vue'
import ApiSearch from '../components/docs/ApiSearch.vue'
import ApiImage from '../components/docs/ApiImage.vue'
import ApiManagement from '../components/docs/ApiManagement.vue'
import ApiWebsocket from '../components/docs/ApiWebsocket.vue'
import ApiOpenapi from '../components/docs/ApiOpenapi.vue'
import UserGuideDocumentManagement from '../components/docs/UserGuideDocumentManagement.vue'
import UserGuideKnowledgeQa from '../components/docs/UserGuideKnowledgeQa.vue'
import UserGuideSearchFeatures from '../components/docs/UserGuideSearchFeatures.vue'
import UserGuideImageManagement from '../components/docs/UserGuideImageManagement.vue'
import UserGuideVersionManagement from '../components/docs/UserGuideVersionManagement.vue'
import UserGuideUserPermissions from '../components/docs/UserGuideUserPermissions.vue'
import UserGuideSecurityScanning from '../components/docs/UserGuideSecurityScanning.vue'
import UserGuideExternalSearch from '../components/docs/UserGuideExternalSearch.vue'
import UserGuideSystemConfig from '../components/docs/UserGuideSystemConfig.vue'
import InstallationDockerDeployment from '../components/docs/InstallationDockerDeployment.vue'
import InstallationKubernetesDeployment from '../components/docs/InstallationKubernetesDeployment.vue'
import InstallationSourceDeployment from '../components/docs/InstallationSourceDeployment.vue'
import InstallationEnvironmentConfig from '../components/docs/InstallationEnvironmentConfig.vue'
import InstallationSecurityConfig from '../components/docs/InstallationSecurityConfig.vue'
import InstallationMonitoringAlerting from '../components/docs/InstallationMonitoringAlerting.vue'
import AdvancedMultimodalConfig from '../components/docs/AdvancedMultimodalConfig.vue'
import AdvancedRetrievalOptimization from '../components/docs/AdvancedRetrievalOptimization.vue'
import AdvancedKnowledgeGraph from '../components/docs/AdvancedKnowledgeGraph.vue'
import AdvancedAiAgent from '../components/docs/AdvancedAiAgent.vue'
import AdvancedK8sMonitoring from '../components/docs/AdvancedK8sMonitoring.vue'
import AdvancedDataMigration from '../components/docs/AdvancedDataMigration.vue'
import AdvancedPerformanceOptimization from '../components/docs/AdvancedPerformanceOptimization.vue'
import AdvancedSecurityHardening from '../components/docs/AdvancedSecurityHardening.vue'
import AdvancedCustomDevelopment from '../components/docs/AdvancedCustomDevelopment.vue'

const route = useRoute()

const docMap: Record<string, any> = {
  'quick-start': {
    component: QuickStart,
    title: '5分钟快速开始'
  },
  'getting-started': {
    component: QuickStart,
    title: '5分钟快速开始'
  },
  'core-concepts': {
    component: CoreConcepts,
    title: '核心概念'
  },
  'system-requirements': {
    component: SystemRequirements,
    title: '系统要求'
  },
  'faq': {
    component: FAQ,
    title: '常见问题'
  },
  'error-troubleshooting': {
    component: ErrorTroubleshooting,
    title: '错误排查'
  },
  'log-analysis': {
    component: LogAnalysis,
    title: '日志分析'
  },
  'performance-issues': {
    component: PerformanceIssues,
    title: '性能问题'
  },
  'security-issues': {
    component: SecurityIssues,
    title: '安全问题'
  },
  'community-support': {
    component: CommunitySupport,
    title: '社区支持'
  },
  'api-overview': {
    component: ApiOverview,
    title: 'API概览'
  },
  'api-document': {
    component: ApiDocument,
    title: '文档管理API'
  },
  'api-qa': {
    component: ApiQa,
    title: '问答API'
  },
  'api-search': {
    component: ApiSearch,
    title: '搜索API'
  },
  'api-image': {
    component: ApiImage,
    title: '图片API'
  },
  'api-management': {
    component: ApiManagement,
    title: '管理API'
  },
  'api-websocket': {
    component: ApiWebsocket,
    title: 'WebSocket API'
  },
  'api-openapi': {
    component: ApiOpenapi,
    title: 'OpenAPI规范'
  },
  'document-management': {
    component: UserGuideDocumentManagement,
    title: '文档管理'
  },
  'knowledge-qa': {
    component: UserGuideKnowledgeQa,
    title: '知识问答'
  },
  'search-features': {
    component: UserGuideSearchFeatures,
    title: '搜索功能'
  },
  'image-management': {
    component: UserGuideImageManagement,
    title: '图片管理'
  },
  'version-management': {
    component: UserGuideVersionManagement,
    title: '版本管理'
  },
  'user-permissions': {
    component: UserGuideUserPermissions,
    title: '用户权限'
  },
  'security-scanning': {
    component: UserGuideSecurityScanning,
    title: '安全扫描'
  },
  'external-search': {
    component: UserGuideExternalSearch,
    title: '联网搜索'
  },
  'system-config': {
    component: UserGuideSystemConfig,
    title: '系统配置'
  },
  'docker-deployment': {
    component: InstallationDockerDeployment,
    title: 'Docker部署'
  },
  'kubernetes-deployment': {
    component: InstallationKubernetesDeployment,
    title: 'Kubernetes部署'
  },
  'source-deployment': {
    component: InstallationSourceDeployment,
    title: '源码部署'
  },
  'environment-config': {
    component: InstallationEnvironmentConfig,
    title: '环境配置'
  },
  'security-config': {
    component: InstallationSecurityConfig,
    title: '安全配置'
  },
  'monitoring-alerting': {
    component: InstallationMonitoringAlerting,
    title: '监控告警'
  },
  'multimodal-config': {
    component: AdvancedMultimodalConfig,
    title: '多模态配置'
  },
  'retrieval-optimization': {
    component: AdvancedRetrievalOptimization,
    title: '检索优化'
  },
  'knowledge-graph': {
    component: AdvancedKnowledgeGraph,
    title: '知识图谱'
  },
  'ai-agent': {
    component: AdvancedAiAgent,
    title: '智能Agent'
  },
  'k8s-monitoring': {
    component: AdvancedK8sMonitoring,
    title: 'K8s监控'
  },
  'data-migration': {
    component: AdvancedDataMigration,
    title: '数据迁移'
  },
  'performance-optimization': {
    component: AdvancedPerformanceOptimization,
    title: '性能优化'
  },
  'security-hardening': {
    component: AdvancedSecurityHardening,
    title: '安全加固'
  },
  'custom-development': {
    component: AdvancedCustomDevelopment,
    title: '二次开发'
  }
}

const docKey = computed(() => route.params.id as string)
const docInfo = computed(() => docMap[docKey.value] || docMap['core-concepts'])
const docComponent = computed(() => docInfo.value.component)
const docTitle = computed(() => docInfo.value.title)
</script>

<style scoped>
.doc-detail-page {
  min-height: 100vh;
}

/* Custom pulse glow animation for return button */
@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
  }
}

.animate-pulse-glow {
  animation: pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>

