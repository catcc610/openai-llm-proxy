"""
External LLM Service - 核心业务逻辑
"""

from __future__ import annotations
import json
import uuid
import asyncio
from typing import Any, AsyncGenerator, Dict, Union
import time
from fastapi import Request
from fastapi.responses import StreamingResponse
from litellm import acompletion
from litellm.utils import ModelResponse

from app.services.base import BaseService, ServiceError
from app.services.external_llm.router import (
    get_provider_from_model,
    resolve_model,
)
from app.services.external_llm.provider_manager import ProviderManager
from logger.logger import get_logger
from config.config import get_external_llm_config

logger = get_logger(__name__)


class ExternalLLMService(BaseService):
    """处理与外部 LLM 提供商交互的核心服务"""

    def __init__(self) -> None:
        super().__init__("external_llm", get_external_llm_config())
        self.provider_manager = ProviderManager()
        logger.info("✅ External LLM 服务已成功初始化")

    def get_models_info(self) -> list[dict[str, Any]]:
        """
        获取所有可用模型的信息，格式遵循 OpenAI /models 接口
        """
        config = get_external_llm_config()
        try:
            models = []
            for model_id, provider in config.get("provider_config", {}).items():
                models.append(
                    {
                        "id": model_id,
                        "object": "model",
                        "created": 1677610602,
                        "owned_by": f"llm-proxy-{provider}",
                        "root": model_id,
                        "parent": None,
                        "permission": [
                            {
                                "id": f"modelperm-{model_id}",
                                "object": "model_permission",
                                "created": 1677610602,
                                "allow_create_engine": False,
                                "allow_sampling": True,
                                "allow_logprobs": True,
                                "allow_search_indices": False,
                                "allow_view": True,
                                "allow_fine_tuning": False,
                                "organization": "*",
                                "group": None,
                                "is_blocking": False,
                            }
                        ],
                    }
                )
            return sorted(models, key=lambda x: str(x["id"]))
        except Exception as e:
            logger.error(f"❌ 获取模型列表失败: {e}")
            raise ServiceError(
                message="获取模型列表失败", error_code="MODEL_LIST_ERROR"
            )

    async def handle_chat_completion(
        self, payload: Dict[str, Any], request: Request
    ) -> Union[StreamingResponse, Dict[str, Any]]:
        """
        处理聊天完成请求，通过LiteLLM转发到相应的LLM提供商
        """
        request_id = (
            request.headers.get("X-Request-ID")
            or getattr(request.state, "request_id", None)
            or str(uuid.uuid4())
        )
        request.state.request_id = request_id

        try:
            t0 = time.time()
            payload = await request.json()
            t1 = time.time()

            model = payload.get("model")
            if not model:
                raise ServiceError(
                    message="请求体中缺少 'model' 字段",
                    error_code="VALIDATION_ERROR",
                )

            stream = payload.get("stream", False)
            logger.info(
                f"📥 [{request_id}] 收到聊天请求: model={model}, stream={stream}"
            )

            litellm_params = self._prepare_litellm_params(payload, request_id)
            t2 = time.time()
            logger.debug(f"🚀 [{request_id}] 开始调用LiteLLM...")

            response = await acompletion(**litellm_params)
            logger.debug(f"✅ [{request_id}] LiteLLM调用成功")

            logger.info(
                f"⏱️ [{request_id}] 解析请求耗时: {(t1 - t0):.3f} 秒, 参数准备耗时: {(t2 - t1):.6f} 秒"
            )

            if stream:
                return await self._handle_streaming_response(
                    response, model, request_id, t2
                )
            else:
                t4 = time.time()
                result = await self._convert_to_response_dict(
                    response, model, request_id
                )
                t5 = time.time()
                logger.info(
                    f"⏱️ [{request_id}] 响应转换耗时: {(t5 - t4):.3f} 秒, 总耗时: {(t5 - t0):.3f} 秒"
                )
                return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ [{request_id}] JSON解析失败: {e}")
            raise ServiceError(
                message="无效的JSON格式", error_code="VALIDATION_JSON_ERROR"
            )
        except Exception as e:
            logger.error(
                "❌ [{request_id}] 聊天完成处理异常: {error_details}",
                request_id=request_id,
                error_details=e,
                exc_info=True,
            )
            raise ServiceError(message=str(e), error_code="CHAT_COMPLETION_ERROR")

    def _prepare_litellm_params(
        self, payload: Dict[str, Any], request_id: str
    ) -> Dict[str, Any]:
        """
        Prepares parameters for LiteLLM by delegating to the appropriate provider handler.
        """
        config = get_external_llm_config()
        model_name = payload.get("model")

        if not model_name or "messages" not in payload:
            raise ServiceError(
                message="Request body must contain 'model' and 'messages'",
                error_code="VALIDATION_REQUEST_ERROR",
            )

        # 1. Determine the provider and the actual model name for LiteLLM
        provider_name = get_provider_from_model(model_name, config)
        model_route = resolve_model(model_name, config)

        # Determine the base model name from the route config
        if isinstance(model_route, dict):
            # For complex routes (like Vertex), get the model name from the dict
            base_model_name = model_route.get("model") or model_name
        else:
            # For simple string routes, the route is the model name
            base_model_name = model_route

        # Always prepend the provider for LiteLLM, e.g., 'vertex_ai/gemini-pro'
        litellm_model = f"{provider_name}/{base_model_name}"
        logger.debug(f"Constructed final LiteLLM model ID: {litellm_model}")

        # 2. Get the specific provider handler from our factory
        provider_handler = self.provider_manager.get_provider(provider_name, config)

        # 3. Prepare a base payload for the handler
        base_payload = payload.copy()
        base_payload["model"] = litellm_model
        base_payload["drop_params"] = True

        # 4. Delegate the final parameter preparation to the handler
        final_params = provider_handler.prepare_litellm_params(
            base_payload, model_route
        )

        logger.debug(
            f"🔍 [{request_id}] Final LiteLLM params from '{provider_handler.__class__.__name__}': {final_params}"
        )
        return final_params

    async def _convert_to_response_dict(
        self, litellm_response: ModelResponse, original_model: str, request_id: str
    ) -> Dict[str, Any]:
        """将非流式LiteLLM响应转换为OpenAI格式的字典"""
        # Run synchronous, CPU-bound operation in a separate thread
        try:
            response_dict = await asyncio.to_thread(litellm_response.model_dump)
            response_dict["model"] = original_model

            # 打印响应ID
            if response_id := response_dict.get("id"):
                logger.info(f"🆔 [{request_id}] 响应ID: {response_id}")

            if usage := response_dict.get("usage"):
                logger.info(f"📊 [{request_id}] Token usage: {usage}")

            return response_dict
        except Exception as e:
            logger.error(f"❌ [{request_id}] 响应转换失败: {e}")
            raise ServiceError("响应格式转换失败", "RESPONSE_CONVERSION_ERROR")

    async def _handle_streaming_response(
        self,
        litellm_stream: Any,
        original_model: str,
        request_id: str,
        start_time: float,
    ) -> StreamingResponse:
        """处理流式响应"""

        async def generate_stream() -> AsyncGenerator[str, None]:
            final_usage = {}
            first_token_time = None
            response_id_logged = False  # 标志位，确保响应ID只打印一次
            try:
                async for chunk in litellm_stream:
                    if first_token_time is None:
                        first_token_time = time.time()
                        elapsed = first_token_time - start_time
                        logger.info(
                            f"⏱️ [{request_id}] 首 token 响应耗时: {elapsed:.3f} 秒"
                        )
                    chunk_dict = chunk.model_dump()
                    chunk_dict["model"] = original_model

                    # 在第一个chunk打印响应ID
                    if not response_id_logged:
                        if response_id := chunk_dict.get("id"):
                            logger.info(
                                f"🆔 [{request_id}] 响应ID (stream): {response_id}"
                            )
                            response_id_logged = True

                    if usage := chunk_dict.get("usage"):
                        final_usage = usage

                    yield f"data: {json.dumps(chunk_dict)}\n\n"
            except Exception as e:
                logger.error(f"❌ [{request_id}] 流处理异常: {e}")
                error_info = {
                    "error": {"message": f"流处理错误: {e}", "type": "STREAM_ERROR"}
                }
                yield f"data: {json.dumps(error_info)}\n\n"
            finally:
                if final_usage:
                    logger.info(
                        f"📊 [{request_id}] Token usage (stream): {final_usage}"
                    )
                yield "data: [DONE]\n\n"

        return StreamingResponse(generate_stream(), media_type="text/event-stream")

    def get_all_provider_stats(self) -> Any:
        """获取所有提供商的状态"""
        config = get_external_llm_config()
        return self.provider_manager.get_all_provider_stats(config)

    async def get_models(self) -> list[dict[str, Any]]:
        """
        获取所有可用模型, 格式遵循OpenAI规范。
        """
        config = get_external_llm_config()
        try:
            models = []
            for model_id, provider in config.get("provider_config", {}).items():
                models.append(
                    {
                        "id": model_id,
                        "object": "model",
                        "created": 1677610602,
                        "owned_by": f"llm-proxy-{provider}",
                        "root": model_id,
                        "parent": None,
                        "permission": [
                            {
                                "id": f"modelperm-{model_id}",
                                "object": "model_permission",
                                "created": 1677610602,
                                "allow_create_engine": False,
                                "allow_sampling": True,
                                "allow_logprobs": True,
                                "allow_search_indices": False,
                                "allow_view": True,
                                "allow_fine_tuning": False,
                                "organization": "*",
                                "group": None,
                                "is_blocking": False,
                            }
                        ],
                    }
                )
            return sorted(models, key=lambda x: str(x["id"]))
        except Exception as e:
            logger.error(f"❌ 获取模型列表失败: {e}")
            raise ServiceError(
                message="获取模型列表失败", error_code="MODEL_LIST_ERROR"
            )