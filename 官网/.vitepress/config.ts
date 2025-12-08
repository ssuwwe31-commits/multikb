import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Knowledge Base',
  description: '企业级知识库管理平台 - 唯一集成ClamAV安全扫描、支持9种文档格式、完整多模态能力',
  base: '/',
  
  // 语言设置
  lang: 'zh-CN',
  
  // 主题配置
  themeConfig: {
    // 网站Logo
    logo: '/logo.png',
    
    // 导航栏
    nav: [
      { text: '首页', link: '/' },
      { text: '功能', link: '/features/' },
      { text: '文档', link: '/docs/' },
      { text: '博客', link: '/blog/' },
      { text: '案例', link: '/cases/' },
      { text: '下载', link: '/download/' },
      { text: '联系我们', link: '/contact/' }
    ],
    
    // 侧边栏
    sidebar: {
      '/features/': [
        { text: '功能概览', link: '/features/' },
        { text: '开源版', link: '/features/open-source' },
        { text: '企业版', link: '/features/enterprise' },
        { text: '版本对比', link: '/features/compare' }
      ],
      '/docs/': [
        { text: '快速开始', link: '/docs/getting-started' },
        { text: '安装部署', link: '/docs/installation' },
        { text: '用户指南', link: '/docs/user-guide' },
        { text: 'API文档', link: '/docs/api' },
        { text: '最佳实践', link: '/docs/best-practices' },
        { text: '常见问题', link: '/docs/faq' }
      ],
      '/blog/': [
        { text: '博客首页', link: '/blog/' },
        { text: '技术文章', link: '/blog/tech' },
        { text: '产品动态', link: '/blog/news' }
      ]
    },
    
    // 社交链接
    socialLinks: [
      { icon: 'github', link: 'https://github.com/your-repo' },
      { icon: 'gitee', link: 'https://gitee.com/your-repo' }
    ],
    
    // 搜索
    search: {
      provider: 'local',
      options: {
        translations: {
          button: {
            buttonText: '搜索',
            buttonAriaLabel: '搜索文档'
          },
          modal: {
            noResultsText: '无法找到相关结果',
            resetButtonTitle: '清除查询条件',
            footer: {
              selectText: '选择',
              navigateText: '切换'
            }
          }
        }
      }
    },
    
    // 编辑链接
    editLink: {
      pattern: 'https://github.com/your-repo/edit/main/官网/:path',
      text: '在 GitHub 上编辑此页'
    },
    
    // 最后更新时间
    lastUpdated: {
      text: '最后更新于',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'medium'
      }
    },
    
    // 页脚
    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2025 Knowledge Base'
    },
    
    // 返回顶部
    returnToTopLabel: '返回顶部',
    
    // 侧边栏标题
    sidebarMenuLabel: '菜单',
    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换到浅色模式',
    darkModeSwitchTitle: '切换到深色模式'
  },
  
  // Markdown配置
  markdown: {
    lineNumbers: true,
    config: (md) => {
      // 可以添加Markdown插件
    }
  },
  
  // 构建配置
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})

