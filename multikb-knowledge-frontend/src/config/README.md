# API 配置说明

## 概述

所有后端 API 地址已统一在 `src/config/api.ts` 中管理，方便切换不同环境。

## 配置方式

### 方式一：使用环境变量（推荐）

在项目根目录创建 `.env` 文件（此文件已被 gitignore，不会提交到仓库）：

```env
# 后端API基础地址（包含 /api 后缀）
VITE_API_BASE_URL=http://localhost:8000/api

# WebSocket基础地址（包含协议）
VITE_WS_BASE_URL=ws://localhost:8000
```

### 方式二：直接修改配置文件

编辑 `src/config/api.ts` 文件，修改默认值：

```typescript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
```

## 使用示例

### 切换到服务器地址

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://192.168.131.158:8081/api
VITE_WS_BASE_URL=ws://192.168.131.158:8081
```

### 切换到本地开发

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000
```

## 注意事项

1. 修改 `.env` 文件后需要重启开发服务器（`npm run dev`）
2. 生产环境构建时，环境变量会在构建时注入，需要重新构建
3. `VITE_API_BASE_URL` 必须包含 `/api` 后缀
4. `VITE_WS_BASE_URL` 必须包含协议前缀（`ws://` 或 `wss://`）
