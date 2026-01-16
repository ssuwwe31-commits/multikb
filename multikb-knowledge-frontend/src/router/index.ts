import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Auth/Login.vue'),
    meta: {
      title: '登录',
      requiresAuth: false
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Auth/Register.vue'),
    meta: {
      title: '注册',
      requiresAuth: false
    }
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/components/layout/AppLayout.vue'),
    redirect: '/home',
    meta: {
      requiresAuth: true
    },
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: {
          title: '首页',
          keepAlive: true,
          requiresAuth: true
        }
      },
      {
        path: 'knowledge-bases',
        name: 'KnowledgeBases',
        component: () => import('@/views/KnowledgeBases/index.vue'),
        meta: {
          title: '知识库管理',
          keepAlive: true
        }
      },
      {
        path: 'knowledge-bases/create',
        name: 'KnowledgeBaseCreate',
        component: () => import('@/views/KnowledgeBases/create.vue'),
        meta: {
          title: '创建知识库',
          keepAlive: false
        }
      },
      {
        path: 'knowledge-bases/:id',
        name: 'KnowledgeBaseDetail',
        component: () => import('@/views/KnowledgeBases/detail.vue'),
        meta: {
          title: '知识库详情',
          keepAlive: false
        }
      },
      {
        path: 'knowledge-bases/:id/edit',
        name: 'KnowledgeBaseEdit',
        component: () => import('@/views/KnowledgeBases/edit.vue'),
        meta: {
          title: '编辑知识库',
          keepAlive: false
        }
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('@/views/Documents/detail.vue'),
        meta: {
          title: '文档详情',
          keepAlive: false
        }
      },
      {
        path: 'documents/:id/edit',
        name: 'DocumentEdit',
        component: () => import('@/views/Documents/edit.vue'),
        meta: {
          title: '编辑文档',
          keepAlive: false
        }
      },
      {
        path: 'documents/:id/versions',
        name: 'DocumentVersions',
        component: () => import('@/views/Documents/versions.vue'),
        meta: {
          title: '文档版本',
          keepAlive: false
        }
      },
      {
        path: 'search/results',
        name: 'SearchResults',
        component: () => import('@/views/Search/results.vue'),
        meta: {
          title: '搜索结果',
          keepAlive: false
        }
      },
      {
        path: 'qa/chat',
        name: 'QAChat',
        component: () => import('@/views/QA/chat.vue'),
        meta: {
          title: '智能问答',
          keepAlive: false
        }
      },
      {
        path: 'qa/history',
        name: 'QAHistory',
        component: () => import('@/views/QA/history.vue'),
        meta: {
          title: '问答历史',
          keepAlive: true
        }
      },
      {
        path: 'images/search',
        name: 'ImageSearch',
        component: () => import('@/views/Images/search.vue'),
        meta: {
          title: '图片搜索',
          keepAlive: false
        }
      },
      {
        path: 'images/:id',
        name: 'ImageViewer',
        component: () => import('@/views/Images/viewer.vue'),
        meta: {
          title: '图片详情',
          keepAlive: false
        }
      },
      {
        path: 'documents/upload',
        name: 'DocumentUpload',
        component: () => import('@/views/Documents/upload.vue'),
        meta: {
          title: '文档上传',
          keepAlive: false
        }
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/Documents/index.vue'),
        meta: {
          title: '文档管理',
          keepAlive: true
        }
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('@/views/Search/index.vue'),
        meta: {
          title: '搜索',
          keepAlive: false
        }
      },
      {
        path: 'qa',
        name: 'QA',
        component: () => import('@/views/QA/index.vue'),
        meta: {
          title: '智能问答',
          keepAlive: true
        }
      },
      {
        path: 'images',
        name: 'Images',
        component: () => import('@/views/Images/index.vue'),
        meta: {
          title: '图片管理',
          keepAlive: true
        }
      },
      {
        path: 'tasks/failures',
        name: 'TaskFailures',
        component: () => import('@/views/Tasks/failures.vue'),
        meta: {
          title: '失败任务中心',
          keepAlive: true
        }
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/Statistics/index.vue'),
        meta: {
          title: '数据统计',
          keepAlive: true
        }
      },
      {
        path: 'exports',
        name: 'Exports',
        component: () => import('@/views/Exports/index.vue'),
        meta: {
          title: '导出管理',
          keepAlive: true
        }
      },
      {
        path: 'observability',
        name: 'Observability',
        component: () => import('@/views/Observability/index.vue'),
        meta: {
          title: '运维诊断',
          keepAlive: false
        }
      },
      {
        path: 'knowledge-graph',
        name: 'KnowledgeGraph',
        component: () => import('@/views/KnowledgeGraph/index.vue'),
        meta: {
          title: '知识图谱',
          keepAlive: true
        }
      },
      {
        path: 'knowledge-graph/tasks',
        name: 'KnowledgeGraphTasks',
        component: () => import('@/views/KnowledgeGraph/Tasks.vue'),
        meta: {
          title: '任务列表',
          keepAlive: true
        }
      },
      {
        path: 'knowledge-graph/entities',
        name: 'KnowledgeGraphEntities',
        component: () => import('@/views/KnowledgeGraph/Entities.vue'),
        meta: {
          title: '实体管理',
          keepAlive: true
        }
      },
      {
        path: 'knowledge-graph/entity-types',
        name: 'KnowledgeGraphEntityTypes',
        component: () => import('@/views/KnowledgeGraph/EntityTypes.vue'),
        meta: {
          title: '实体类型管理',
          keepAlive: true
        }
      },
      // 代码库分析（2026-01-12 新增）
      {
        path: 'code-repository',
        name: 'CodeRepository',
        component: () => import('@/views/CodeRepository/index.vue'),
        meta: {
          title: '代码库分析',
          keepAlive: true
        }
      },
      {
        path: 'code-repository/:id',
        name: 'CodeRepositoryDetail',
        component: () => import('@/views/CodeRepository/detail.vue'),
        meta: {
          title: '代码库详情',
          keepAlive: false
        }
      }
    ]
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/Error/403.vue')
  },
  {
    path: '/500',
    name: 'ServerError',
    component: () => import('@/views/Error/500.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/Error/404.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
import { useAppStore } from '@/stores/modules/app'
import { useUserStore } from '@/stores/modules/user'

router.beforeEach(async (to, from, next) => {
  const appStore = useAppStore()
  const userStore = useUserStore()
  
  // 设置标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - ${appStore.appTitle}`
  }
  
  // 检查是否需要认证
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  
  if (requiresAuth) {
    // 检查是否有token
    const token = localStorage.getItem('access_token')
    if (!token) {
      next('/login')
      return
    }
    
    // 如果有token但没有用户信息，尝试获取
    if (!userStore.user) {
      try {
        await userStore.fetchUserInfo()
      } catch (error) {
        // 获取失败，清除token并跳转登录
        userStore.clearAuth()
        next('/login')
        return
      }
    }
  } else {
    // 如果已登录，访问登录/注册页面时跳转到首页
    if ((to.path === '/login' || to.path === '/register') && userStore.isAuthenticated) {
      next('/')
      return
    }
  }
  
  next()
})

export default router
