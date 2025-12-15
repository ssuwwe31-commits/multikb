"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.api.v1.routes import websocket as ws_routes
from app.api.routes import query as query_routes
from app.api.routes import tables as tables_routes
from app.core.exceptions import setup_exception_handlers
from app.core.logging import logger
from app.config.settings import settings
from app.middleware.logging import logging_middleware
import os
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动时检查中间件连接"""
    # Windows 下配置 asyncio 以更好地处理连接关闭
    if os.name == "nt":
        try:
            # 设置 Windows 事件循环策略（如果尚未设置）
            if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass
    
    # 启动时检查
    logger.info("正在检查中间件连接...")
    logger.info(f"配置文件位置: {settings.HOST}:{settings.PORT}")
    
    # 检查 MySQL
    try:
        logger.info(f"连接 MySQL: {settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, '***')}")
        from app.config.database import engine
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        logger.info("✅ MySQL 连接正常")
    except Exception as e:
        logger.error(f"❌ MySQL 连接失败: {e}")
    
    # 检查 Redis
    try:
        logger.info(f"连接 Redis: {settings.REDIS_URL}")
        from app.config.redis import redis_client
        redis_client.ping()
        logger.info("✅ Redis 连接正常")
    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}")
    
    # 检查 MinIO
    try:
        logger.info(f"连接 MinIO: {settings.MINIO_ENDPOINT} (用户: {settings.MINIO_ROOT_USER})")
        from app.config.minio import minio_client
        minio_client.list_buckets()
        logger.info("✅ MinIO 连接正常")
    except Exception as e:
        logger.error(f"❌ MinIO 连接失败: {e}")
    
    # 检查 OpenSearch
    try:
        logger.info(f"连接 OpenSearch: {settings.OPENSEARCH_URL} (SSL: {settings.OPENSEARCH_USE_SSL})")
        from app.config.opensearch import opensearch_client
        opensearch_client.cluster.health()
        logger.info("✅ OpenSearch 连接正常")
        
        # 确保 resource_events 索引存在
        try:
            from app.services.opensearch_service import OpenSearchService
            opensearch_service = OpenSearchService()
            await opensearch_service.ensure_resource_events_index()
            logger.info("✅ resource_events 索引已就绪")
        except Exception as e:
            logger.warning(f"⚠️ 确保 resource_events 索引存在失败: {e}")
    except Exception as e:
        logger.error(f"❌ OpenSearch 连接失败: {e}")
    
    logger.info("🚀 服务器启动完成")
    yield
    logger.info("👋 服务器关闭")
    
    # 关闭NebulaGraph连接池
    try:
        from app.services.graph_storage_service import close_global_graph_storage
        close_global_graph_storage()
    except Exception as e:
        logger.debug(f"关闭NebulaGraph连接池时出错（可忽略）: {e}")


app = FastAPI(
    title="SPX Knowledge Base API",
    description="知识库系统后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 添加受信任主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# 请求日志中间件（记录每个请求的开始、结束、状态码与耗时）
app.middleware("http")(logging_middleware)

# 认证中间件（在所有/api路径上要求认证，除了认证相关的接口）
from app.middleware.auth import auth_middleware
app.middleware("http")(auth_middleware)

# 注册API路由 - 按照设计文档要求使用 /api 前缀
app.include_router(api_router, prefix="/api")
# 新增查询上下文路由
app.include_router(query_routes.router, prefix="/api")
# 新增表格懒加载路由
app.include_router(tables_routes.router, prefix="/api")

# 兼容前端 WebSocket 直接连接 /ws/... 的路径（不走 /api 前缀）
app.include_router(ws_routes.router, prefix="/ws")

# 兼容性图片代理（无 /api 前缀的场景，需要认证）
from fastapi import HTTPException, Depends, Request, status, Query
from app.services.minio_storage_service import MinioStorageService
from app.core.logging import logger
from fastapi.responses import Response
from app.dependencies.auth import get_current_user

@app.get("/images/file")
async def compat_image_proxy(request: Request, object: str = Query(..., description="MinIO对象路径")):
    """兼容性图片代理（无 /api 前缀的场景，需要认证）"""
    # 自己处理认证（因为不在 /api/ 路径下，中间件不会处理）
    from app.core.security import verify_token
    
    # 从请求头或查询参数获取token
    authorization = request.headers.get("Authorization")
    token = None
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    else:
        # 尝试从查询参数获取token（用于<img>标签请求）
        token = request.query_params.get("token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 验证令牌
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌无效",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        minio = MinioStorageService()
        data = minio.download_file(object)
        lower = object.lower()
        if lower.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif lower.endswith(".png"):
            content_type = "image/png"
        elif lower.endswith(".gif"):
            content_type = "image/gif"
        elif lower.endswith(".webp"):
            content_type = "image/webp"
        else:
            content_type = "application/octet-stream"
        return Response(content=data, media_type=content_type)
    except Exception as e:
        logger.error(f"兼容图片代理错误: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail="图片不存在或无法访问")

# 设置异常处理器
setup_exception_handlers(app)

@app.get("/")
async def root():
    """根路径"""
    return {"message": "SPX Knowledge Base API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """健康检查 - 检查所有中间件连接状态"""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {}
    }
    
    # 检查 MySQL
    try:
        from app.config.database import engine
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        health_status["services"]["mysql"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["mysql"] = {"status": "error", "message": str(e)}
    
    # 检查 Redis
    try:
        from app.config.redis import redis_client
        redis_client.ping()
        health_status["services"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["redis"] = {"status": "error", "message": str(e)}
    
    # 检查 MinIO
    try:
        from app.config.minio import minio_client
        minio_client.list_buckets()
        health_status["services"]["minio"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["minio"] = {"status": "error", "message": str(e)}
    
    # 检查 OpenSearch
    try:
        from app.config.opensearch import opensearch_client
        opensearch_client.cluster.health()
        health_status["services"]["opensearch"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["opensearch"] = {"status": "error", "message": str(e)}
    
    return health_status
