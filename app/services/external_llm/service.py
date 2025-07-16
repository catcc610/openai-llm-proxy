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
from litellm.llms.anthropic.experimental_pass_through.adapters.transformation import (
    AnthropicAdapter,
)
from datetime import datetime

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
        self, request: Request
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
        logger.info(
            f"🔍 [{request_id}] 准备LiteLLM参数: model={model_name}, max_tokens={payload.get('max_tokens', 'None')}"
        )
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

        # Add stream_options for streaming requests if not already present
        if base_payload.get("stream", False) and "stream_options" not in base_payload:
            base_payload["stream_options"] = {"include_usage": True}
            logger.debug(f"🔄 [{request_id}] 添加流式usage统计参数: stream_options")

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
            response_dict: Dict[str, Any] = await asyncio.to_thread(
                litellm_response.model_dump
            )
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
                            f"⏱️ [{request_id}] 首 token 响应耗时: {elapsed:.3f} 秒， {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"
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

    async def handle_anthropic_messages(
        self, request: Request
    ) -> Union[StreamingResponse, Dict[str, Any]]:
        """
        处理 Anthropic 消息格式请求，利用 LiteLLM 的转换能力

        流程：
        1. 接收 Anthropic 格式的请求
        2. 使用 LiteLLM AnthropicAdapter 转换为 OpenAI 格式
        3. 调用 acompletion 生成响应
        4. 将 OpenAI 格式响应转换回 Anthropic 格式
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
                f"📥 [{request_id}] 收到 Anthropic 消息请求: model={model}, stream={stream}"
            )

            # 1. 使用 LiteLLM AnthropicAdapter 转换请求格式
            anthropic_adapter = AnthropicAdapter()

            # 注意：translate_completion_input_params 会修改原始字典，所以使用副本
            payload_for_conversion = payload.copy()
            openai_request = anthropic_adapter.translate_completion_input_params(
                payload_for_conversion
            )
            if not openai_request:
                raise ServiceError(
                    message="Anthropic 请求格式转换失败",
                    error_code="FORMAT_CONVERSION_ERROR",
                )

            # ChatCompletionRequest 是 Pydantic 模型，转换为字典
            openai_payload = (
                openai_request.model_dump()
                if hasattr(openai_request, "model_dump")
                else dict(openai_request)
            )
            logger.debug(f"✅ [{request_id}] Anthropic -> OpenAI 格式转换成功")

            # 2. 准备 LiteLLM 参数
            litellm_params = self._prepare_litellm_params(openai_payload, request_id)
            t2 = time.time()
            logger.debug(f"🚀 [{request_id}] 开始调用 LiteLLM...")

            # 3. 调用 LiteLLM 生成响应
            response = await acompletion(**litellm_params)
            logger.debug(f"✅ [{request_id}] LiteLLM 调用成功")

            logger.info(
                f"⏱️ [{request_id}] 解析请求耗时: {(t1 - t0):.3f} 秒, 参数准备耗时: {(t2 - t1):.6f} 秒"
            )

            # 4. 处理响应转换
            if stream:
                return await self._handle_anthropic_streaming_response(
                    response, model, request_id, t2
                )
            else:
                t4 = time.time()
                result = await self._convert_to_anthropic_response_dict(
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
                "❌ [{request_id}] Anthropic 消息处理异常: {error_details}",
                request_id=request_id,
                error_details=e,
                exc_info=True,
            )
            raise ServiceError(message=str(e), error_code="ANTHROPIC_MESSAGES_ERROR")

    async def _convert_to_anthropic_response_dict(
        self, litellm_response: ModelResponse, original_model: str, request_id: str
    ) -> Dict[str, Any]:
        """将 LiteLLM OpenAI 格式响应转换为 Anthropic 格式"""
        try:
            anthropic_adapter = AnthropicAdapter()

            # 使用 LiteLLM 适配器转换响应
            anthropic_response = anthropic_adapter.translate_completion_output_params(
                litellm_response
            )
            if not anthropic_response:
                logger.error(f"❌ [{request_id}] Anthropic 响应转换返回 None")
                raise ServiceError(
                    "Anthropic response conversion failed.",
                    "ANTHROPIC_RESPONSE_CONVERSION_ERROR",
                )

            # 检查返回的是 Pydantic 模型还是字典
            if hasattr(anthropic_response, "model_dump"):
                # Pydantic 模型，调用 model_dump()
                response_dict: Dict[str, Any] = anthropic_response.model_dump()
            elif hasattr(anthropic_response, "dict"):
                # Pydantic 模型（旧版本），调用 dict()
                response_dict = anthropic_response.dict()
            else:
                # 已经是字典，直接使用
                if isinstance(anthropic_response, dict):
                    response_dict = anthropic_response
                else:
                    response_dict = dict(anthropic_response)

            response_dict["model"] = original_model

            # 打印响应ID
            if response_id := response_dict.get("id"):
                logger.info(f"🆔 [{request_id}] Anthropic 响应ID: {response_id}")

            if usage := response_dict.get("usage"):
                logger.info(f"📊 [{request_id}] Token usage: {usage}")

            logger.debug(f"✅ [{request_id}] OpenAI -> Anthropic 格式转换成功")

            return response_dict

        except Exception as e:
            logger.error(
                f"❌ [{request_id}] Anthropic 响应转换失败: {e}", exc_info=True
            )
            raise ServiceError(
                "Anthropic 响应格式转换失败", "ANTHROPIC_RESPONSE_CONVERSION_ERROR"
            )

    async def _handle_anthropic_streaming_response(
        self,
        litellm_stream: Any,
        original_model: str,
        request_id: str,
        start_time: float,
    ) -> StreamingResponse:
        """处理 Anthropic 格式的流式响应"""

        async def openai_usage_logging_stream(stream: Any) -> AsyncGenerator[Any, None]:
            """代理流时记录 OpenAI 的 usage，并透传数据块"""
            final_usage = None
            async for chunk in stream:
                if hasattr(chunk, "usage") and chunk.usage:
                    final_usage = chunk.usage
                yield chunk
            if final_usage:
                try:
                    usage_dict = (
                        final_usage.model_dump()
                        if hasattr(final_usage, "model_dump")
                        else dict(final_usage)
                    )
                    logger.info(
                        f"📊 [{request_id}] OpenAI format usage (from stream): {json.dumps(usage_dict)}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [{request_id}] 无法序列化 usage 信息: {e}")

        async def generate_anthropic_stream() -> AsyncGenerator[str, None]:
            first_token_time = None

            try:
                # 使用包装器记录 OpenAI usage
                logged_litellm_stream = openai_usage_logging_stream(litellm_stream)

                anthropic_adapter = AnthropicAdapter()

                # 使用 LiteLLM 适配器的流式转换
                anthropic_stream = (
                    anthropic_adapter.translate_completion_output_params_streaming(
                        logged_litellm_stream, original_model
                    )
                )

                if not anthropic_stream:
                    logger.error(f"❌ [{request_id}] Anthropic 适配器未能创建流。")
                    raise ServiceError(
                        "Anthropic adapter failed to create a stream.",
                        "ANTHROPIC_STREAM_CREATION_ERROR",
                    )

                async for chunk_data in anthropic_stream:
                    if first_token_time is None:
                        first_token_time = time.time()
                        elapsed = first_token_time - start_time
                        logger.info(
                            f"⏱️ [{request_id}] 首 token 响应耗时: {elapsed:.3f} 秒， {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"
                        )

                    # LiteLLM 适配器可能返回字节流或字符串
                    if isinstance(chunk_data, bytes):
                        yield chunk_data.decode("utf-8")
                    elif isinstance(chunk_data, str):
                        yield chunk_data
                    else:
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                logger.debug(f"✅ [{request_id}] Anthropic 流式转换完成")

            except Exception as e:
                logger.error(
                    f"❌ [{request_id}] Anthropic 流处理异常: {e}", exc_info=True
                )
                error_info = {
                    "error": {
                        "message": f"Anthropic 流处理错误: {e}",
                        "type": "ANTHROPIC_STREAM_ERROR",
                    }
                }
                yield f"data: {json.dumps(error_info)}\n\n"
            finally:
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_anthropic_stream(), media_type="text/event-stream"
        )

    def get_all_provider_stats(self) -> Dict[str, Any]:
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
