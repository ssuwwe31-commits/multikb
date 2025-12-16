import uvicorn
import os
import asyncio

from app.config.settings import settings


if __name__ == "__main__":
    # Windows下使用 SelectorEventLoop，避免 Ctrl+C 无法中断的问题
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    # 明确默认禁用 reload，避免子进程导致的信号处理问题
    enable_reload = os.getenv("ENABLE_RELOAD", "false").lower() == "true"

    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=enable_reload,
            reload_excludes=["*.pyc", "__pycache__"] if enable_reload else None,
            workers=1,
            log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
        )
    except KeyboardInterrupt:
        # 显式捕获，确保进程快速退出
        pass
