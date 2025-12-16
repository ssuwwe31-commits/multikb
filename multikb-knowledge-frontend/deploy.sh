#!/bin/bash

# 前端快速部署脚本
# 使用方法: ./deploy.sh [后端API地址]

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   MultiKB Knowledge Frontend 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装，请先安装 Docker Compose${NC}"
    exit 1
fi

# 获取后端 API 地址（参数或环境变量）
BACKEND_API_URL=${1:-${BACKEND_API_URL:-http://192.168.131.158:8081}}

echo -e "${YELLOW}后端 API 地址: ${BACKEND_API_URL}${NC}"

# 更新 nginx 配置中的后端地址
if [ -f "docker/nginx/default.conf" ]; then
    # 根据操作系统使用不同的 sed 命令
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|proxy_pass http://.*;|proxy_pass ${BACKEND_API_URL};|g" docker/nginx/default.conf
    else
        # Linux
        sed -i "s|proxy_pass http://.*;|proxy_pass ${BACKEND_API_URL};|g" docker/nginx/default.conf
    fi
    echo -e "${GREEN}✓ Nginx 配置已更新${NC}"
else
    echo -e "${YELLOW}警告: docker/nginx/default.conf 不存在，跳过配置更新${NC}"
fi

# 停止旧容器
echo -e "${YELLOW}停止旧容器...${NC}"
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true

# 构建镜像
echo -e "${YELLOW}构建 Docker 镜像...${NC}"
docker-compose build --no-cache || docker compose build --no-cache

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
docker-compose up -d || docker compose up -d

# 等待服务启动
sleep 3

# 检查服务状态
if docker-compose ps | grep -q "Up" || docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  部署成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "前端访问地址: ${GREEN}http://$(hostname -I | awk '{print $1}'):3000${NC}"
    echo -e "或: ${GREEN}http://localhost:3000${NC}"
    echo ""
    echo -e "查看日志: ${YELLOW}docker-compose logs -f${NC}"
    echo -e "停止服务: ${YELLOW}docker-compose down${NC}"
else
    echo -e "${RED}部署失败，请检查日志: docker-compose logs${NC}"
    exit 1
fi

