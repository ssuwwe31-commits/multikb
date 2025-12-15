import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import autoprefixer from 'autoprefixer'

// 从环境变量获取后端地址，默认 localhost:8000
const getBackendTarget = () => {
  const apiBaseUrl = process.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
  // 移除 /api 后缀，获取基础地址
  return apiBaseUrl.replace('/api', '')
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  css: {
    postcss: {
      plugins: [
        autoprefixer(),
      ],
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: getBackendTarget(),
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'terser',
    chunkSizeWarningLimit: 1000
  }
})
