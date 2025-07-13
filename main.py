import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.config import get_server_config, get_external_llm_config
from logger.logger import get_logger
from app.routers.external_llm import get_external_llm_router
from app.services.external_llm import get_external_llm_service
from app.common.errors import setup_error_handlers

"""
LLM Proxy 主应用入口
"""

# Load environment variables from .env file
load_dotenv()

# 获取一个 logger 实例以在模块级别使用
logger = get_logger(__name__)

server_config = get_server_config()


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例
    工厂函数 - 用于多进程环境
    """
    logger.info("🚀 开始创建 FastAPI 应用...")

    # 验证关键配置是否存在
    if not get_external_llm_config():
        logger.error("❌ 外部LLM配置缺失，服务无法启动。")
        raise RuntimeError("External LLM configuration is missing.")

    app = FastAPI(
        title="LLM Proxy",
        description="一个统一的、可扩展的、面向生产的 LLM 代理服务",
        version="2.0.0",
    )

    # 设置错误处理器
    setup_error_handlers(app)

    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 预热并加载路由
    logger.info("🔧 正在初始化并加载外部 LLM 服务和路由...")
    get_external_llm_service()  # Pre-warm the service
    external_llm_router = get_external_llm_router()
    app.include_router(external_llm_router.router)

    @app.get("/health", tags=["Health Check"])
    async def health_check() -> dict:
        return {"status": "ok"}

    logger.info("✅ FastAPI 应用已成功创建")
    return app


if __name__ == "__main__":
    import uvicorn

    # ✅ 修正：使用导入字符串 + factory模式
    cpu_count = os.cpu_count()
    default_workers = (cpu_count + 1) if cpu_count is not None else 4

    uvicorn.run(
        "main:create_app",  # 导入字符串 ✅
        factory=True,  # 工厂函数模式 ✅
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8080),
        log_level=server_config.get("log_level", "info"),
        workers=server_config.get("workers", default_workers),
    )
