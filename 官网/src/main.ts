import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/main.css'

// 初始化dark模式（在应用挂载前）
const initDarkMode = () => {
  if (typeof window === 'undefined') return
  
  const html = document.documentElement
  const saved = window.localStorage?.getItem('vueuse-color-scheme')
  
  if (saved === 'dark') {
    html.classList.add('dark')
  } else if (saved === 'light') {
    html.classList.remove('dark')
  } else {
    // 检查系统偏好
    const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
    if (prefersDark) {
      html.classList.add('dark')
      window.localStorage?.setItem('vueuse-color-scheme', 'dark')
    } else {
      html.classList.remove('dark')
      window.localStorage?.setItem('vueuse-color-scheme', 'light')
    }
  }
}

// 在创建应用前初始化
initDarkMode()

const app = createApp(App)
app.use(router)
app.mount('#app')

