"""
Rate Limit Middleware
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.config.redis import get_redis
import time
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    """限流中间件"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.redis = get_redis()
    
    async def __call__(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = request.client.host
        
        # 生成限流键
        current_minute = int(time.time() // 60)
        rate_limit_key = f"rate_limit:{client_ip}:{current_minute}"
        
        try:
            # 检查当前分钟内的请求数
            current_requests = self.redis.get(rate_limit_key)
            
            if current_requests is None:
                # 第一次请求，设置计数器
                self.redis.setex(rate_limit_key, 60, 1)
            else:
                current_requests = int(current_requests)
                
                if current_requests >= self.requests_per_minute:
                    # 超过限流阈值
                    logger.warning(f"IP {client_ip} 触发限流")
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"error": "请求过于频繁，请稍后再试"}
                    )
                else:
                    # 增加计数器
                    self.redis.incr(rate_limit_key)
            
            # 处理请求
            response = await call_next(request)
            
            # 添加限流信息到响应头
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(
                self.requests_per_minute - int(self.redis.get(rate_limit_key) or 0)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"限流中间件错误: {e}")
            # 如果Redis出错，允许请求通过
            return await call_next(request)
