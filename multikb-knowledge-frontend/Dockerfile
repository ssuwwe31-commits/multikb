FROM node:18-alpine AS builder

WORKDIR /app

# 仅复制依赖清单，利用 Docker 缓存
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production=false

# 复制源代码
COPY . .

# 构建项目（跳过 TypeScript 严格类型检查，只运行 vite build）
RUN npm run build:prod

# 生产阶段：使用 nginx 服务静态文件
FROM nginx:alpine

# 复制构建产物到 nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

