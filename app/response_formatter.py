"""
LLM Proxy - Response Formatting Utilities

将LiteLLM的响应对象转换为OpenAI兼容的字典或流式数据块。
"""

import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse
from litellm.utils import CustomStreamWrapper, ModelResponse

logger = logging.getLogger(__name__)


def convert_litellm_response_to_dict(
    litellm_response: ModelResponse, original_model: str
) -> dict[str, Any]:
    """将LiteLLM的非流式响应转换为与OpenAI兼容的字典格式"""
    try:
        response_dict: dict[str, Any] = litellm_response.model_dump()
        response_dict["model"] = original_model
        return response_dict
    except Exception as e:
        logger.error(f"❌ LiteLLM响应转换为字典时出错: {e}", exc_info=True)
        # 如果转换失败，创建一个备用的错误响应
        return {
            "id": f"chatcmpl-error-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": original_model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"处理后端响应时发生内部错误: {str(e)}",
                    },
                    "finish_reason": "error",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


async def handle_litellm_streaming_response(
    litellm_stream: CustomStreamWrapper, original_model: str, request_id: str
) -> StreamingResponse:
    """处理LiteLLM的流式响应，生成兼容OpenAI的SSE流"""

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            logger.info(f"🌊 [{request_id}] 开始处理流式响应...")
            async for chunk in litellm_stream:
                chunk_dict = chunk.model_dump()
                chunk_dict["model"] = original_model
                yield f"data: {json.dumps(chunk_dict)}\n\n"
            logger.info(f"✅ [{request_id}] 流式响应处理完成")
        except Exception as e:
            logger.error(
                f"❌ [{request_id}] 流式响应处理中发生错误: {e}", exc_info=True
            )
            error_chunk = {
                "id": f"chatcmpl-error-{request_id}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": original_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": f"流式处理错误: {str(e)}",
                        },
                        "finish_reason": "error",
                    }
                ],
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx-specific header for disabling buffering
        },
    )
