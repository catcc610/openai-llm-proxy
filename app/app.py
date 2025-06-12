"""
LLM Proxy Service - FastAPI Main Application
"""

# 标准库导入
import logging
import uuid
from typing import Dict, Any, Union

# 第三方库导入
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# LiteLLM导入
from litellm import acompletion
from litellm.utils import ModelResponse, CustomStreamWrapper

# 本地应用导入
from app.config import get_config
from app.router import resolve_model
from app.errors import setup_error_handlers, handle_proxy_error
from app.middleware import RequestIDMiddleware, LoggingMiddleware
from app.models import ChatCompletionRequest
from app.response_formatter import (
    convert_litellm_response_to_dict,
    handle_litellm_streaming_response,
)


def create_app() -> FastAPI:
    """创建并配置FastAPI应用实例"""

    # 获取日志记录器
    logger = logging.getLogger(__name__)
    logger.info("🚀 正在初始化LLM Proxy Service...")

    # 创建FastAPI应用实例
    app = FastAPI(
        title="LLM Proxy Service",
        description="基于LiteLLM的多厂商LLM代理服务",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 设置错误处理器
    setup_error_handlers(app)

    # 添加中间件（注意顺序：最后添加的最先执行）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境中应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加请求日志中间件
    app.add_middleware(LoggingMiddleware, log_body=False)

    # 添加请求ID中间件（最先执行）
    app.add_middleware(RequestIDMiddleware)

    logger.info("✅ FastAPI应用初始化完成")
    return app


# 创建应用实例
app = create_app()

# 获取日志记录器（在app创建后）
logger = logging.getLogger(__name__)


@app.get("/")
async def root() -> Dict[str, str]:
    """健康检查端点"""
    return {
        "message": "LLM Proxy Service is running",
        "version": "0.1.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """详细健康检查"""
    return {"status": "healthy", "service": "llm-proxy", "version": "0.1.0"}


@app.get("/config")
async def get_config_info() -> Dict[str, Any]:
    """获取配置信息（不包含敏感数据）"""
    try:
        config = get_config()
        return {
            "server": config.server.model_dump(),
            "proxy": config.proxy.model_dump(),
            "available_models": list(config.model_routes.keys()),
            "security_enabled": len(config.security.api_keys) > 0,
        }
    except Exception as e:
        return {"error": f"配置获取失败: {str(e)}"}


# ================================
# OpenAI 兼容的 API 端点
# ================================


@app.post("/v1/chat/completions", response_model=None, status_code=200)
async def chat_completions(
    request: ChatCompletionRequest, http_request: Request
) -> Union[Dict[str, Any], StreamingResponse]:
    """
    OpenAI 兼容的聊天完成端点 - 支持多模态、流式和工具调用。
    通过LiteLLM将请求路由并转发到相应的LLM提供商。
    """
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4()))

    try:
        logger.info(
            f"📥 [{request_id}] 接收到聊天请求: model={request.model}, stream={request.stream}"
        )
        if any(isinstance(msg.content, list) for msg in request.messages):
            logger.info(f"🖼️ [{request_id}] 请求包含多模态内容")

        litellm_model = resolve_model(request.model)
        logger.info(f"🔄 [{request_id}] 模型路由: {request.model} -> {litellm_model}")

        litellm_params = request.to_litellm_params(litellm_model=litellm_model)

        # 敏感信息不应被记录到日志
        # logger.debug(f"🚀 [{request_id}] 调用LiteLLM参数: {json.dumps(litellm_params, indent=2, ensure_ascii=False)}")

        response: Union[ModelResponse, CustomStreamWrapper] = await acompletion(
            **litellm_params
        )

        if request.stream:
            # 确保返回的是流式包装器
            if not isinstance(response, CustomStreamWrapper):
                # 这里可以引发一个自定义的内部错误
                raise TypeError("预期得到流式响应，但收到了非流式响应")
            logger.info(f"➡️ [{request_id}] 转发流式响应")
            return await handle_litellm_streaming_response(
                response, request.model, request_id
            )
        else:
            # 确保返回的是模型响应对象
            if not isinstance(response, ModelResponse):
                raise TypeError("预期得到非流式响应，但收到了流式响应")
            logger.info(f"⬅️ [{request_id}] 转发非流式响应")
            return convert_litellm_response_to_dict(response, request.model)

    except Exception as e:
        return await handle_proxy_error(http_request, e)
