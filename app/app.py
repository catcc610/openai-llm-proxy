"""
LLM Proxy Service - FastAPI Main Application
"""

# 标准库导入
import json
import logging
import os
import time
import uuid
from typing import Dict, Any, Union

# 第三方库导入
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# LiteLLM导入
from litellm import acompletion

# 本地应用导入
from app.config import get_config, reload_config
from app.router import resolve_model, get_provider_from_model
from app.errors import setup_error_handlers, handle_streaming_error
from app.middleware import RequestIDMiddleware, LoggingMiddleware
from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    MessageRole,
    ChatMessage,
    Choice,
    Usage,
    ChoiceFinishReason,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 设置LiteLLM日志级别（使用环境变量）
os.environ["LITELLM_LOG"] = "INFO"  # 更新的日志设置方式

# 注意：API密钥现在通过config.py自动设置，无需手动处理

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


@app.post("/config/reload")
async def reload_config_endpoint() -> Dict[str, str]:
    """重新加载配置"""
    try:
        reload_config()
        return {"message": "配置重新加载成功"}
    except Exception as e:
        return {"error": f"配置重新加载失败: {str(e)}"}


# ================================
# OpenAI 兼容的 API 端点
# ================================


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest, http_request: Request
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """
    OpenAI 兼容的聊天完成端点
    通过LiteLLM转发请求到相应的LLM提供商
    """
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4()))

    try:
        # 记录请求信息
        logger.info(f"📥 [{request_id}] 聊天完成请求:")
        logger.info(f"   模型: {request.model}")
        logger.info(f"   消息数量: {len(request.messages)}")
        logger.info(f"   温度: {request.temperature}")
        logger.info(f"   流式: {request.stream}")

        # 使用路由器解析模型
        litellm_model = resolve_model(request.model)
        provider = get_provider_from_model(request.model)
        logger.info(
            f"🔄 [{request_id}] 模型路由: {request.model} -> {litellm_model} (提供商: {provider})"
        )

        # 使用请求模型的方法自动转换为LiteLLM参数
        litellm_params = request.to_litellm_params(litellm_model)

        logger.debug(
            f"🚀 [{request_id}] 调用LiteLLM，参数: {json.dumps(litellm_params, indent=2, ensure_ascii=False)}"
        )

        # 调用LiteLLM (异步调用)
        response = await acompletion(**litellm_params)

        if request.stream:
            # 流式响应处理
            return await handle_litellm_streaming_response(
                response, request.model, request_id
            )
        else:
            # 非流式响应处理
            return convert_litellm_response(response, request.model)

    except Exception as e:
        # 使用我们的错误处理系统
        from app.errors import handle_proxy_error

        return await handle_proxy_error(http_request, e)


def convert_litellm_response(
    litellm_response: Any, original_model: str
) -> ChatCompletionResponse:
    """将LiteLLM响应转换为我们的Pydantic模型"""
    try:
        # LiteLLM返回的响应已经是OpenAI格式，直接转换
        response_dict = (
            litellm_response.model_dump()
            if hasattr(litellm_response, "model_dump")
            else dict(litellm_response)
        )

        # 确保所有必需的字段都存在
        if "id" not in response_dict:
            response_dict["id"] = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        if "created" not in response_dict:
            response_dict["created"] = int(time.time())
        if "object" not in response_dict:
            response_dict["object"] = "chat.completion"

        # 确保返回原始请求的模型名称，而不是LiteLLM的内部模型名
        response_dict["model"] = original_model

        return ChatCompletionResponse(**response_dict)
    except Exception as e:
        print(f"❌ 响应转换错误: {e}")
        # 创建备用响应
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            object="chat.completion",
            created=int(time.time()),
            model=original_model,
            choices=[
                Choice(
                    index=0,
                    message=ChatMessage(
                        role=MessageRole.ASSISTANT, content=str(litellm_response)
                    ),
                    finish_reason=ChoiceFinishReason.STOP,
                )
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )


async def handle_litellm_streaming_response(
    litellm_stream: Any, original_model: str, request_id: str | None = None
) -> StreamingResponse:
    """处理LiteLLM的流式响应"""

    async def generate_stream() -> Any:
        try:
            # 异步迭代流式响应
            async for chunk in litellm_stream:
                # LiteLLM返回的流式响应已经是OpenAI格式
                chunk_dict = (
                    chunk.model_dump() if hasattr(chunk, "model_dump") else dict(chunk)
                )

                # 确保chunk有正确的格式
                if "object" not in chunk_dict:
                    chunk_dict["object"] = "chat.completion.chunk"
                if "id" not in chunk_dict:
                    chunk_dict["id"] = f"chatcmpl-{request_id or uuid.uuid4().hex[:8]}"
                if "created" not in chunk_dict:
                    chunk_dict["created"] = int(time.time())

                # 确保返回原始请求的模型名称
                chunk_dict["model"] = original_model

                yield f"data: {json.dumps(chunk_dict, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"❌ [{request_id}] 流式响应处理错误: {e}")
            # 发送错误响应块
            error_data = await handle_streaming_error(e, original_model, request_id)
            yield error_data
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        },
    )
