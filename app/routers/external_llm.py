"""
External LLM 路由 - 使用新的四层架构
"""

from __future__ import annotations
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Union
from app.routers.base import BaseRouter
from app.services.external_llm import get_external_llm_service


class ExternalLLMRouter(BaseRouter):
    """External LLM 路由"""

    def __init__(self) -> None:
        self.llm_service = get_external_llm_service()
        super().__init__(prefix="/v1", tags=["external_llm"])

    def _setup_routes(self) -> None:
        """设置 LLM 相关路由"""

        @self.router.get("/models", summary="获取可用模型列表")
        async def list_models() -> dict[str, Any]:
            """
            获取所有可用模型, 格式遵循OpenAI规范。
            """
            models_list = await self.llm_service.get_models()
            return {"data": models_list}

        @self.router.post(
            "/chat/completions",
            summary="处理聊天请求",
            response_model=None,
        )
        async def chat_completions(
            request: Request,
        ) -> Union[Dict[str, Any], StreamingResponse]:
            """
            处理聊天完成请求，支持流式和非流式响应。
            """
            payload = await request.json()
            return await self.llm_service.handle_chat_completion(payload, request)


def get_external_llm_router() -> ExternalLLMRouter:
    """获取 External LLM 路由实例"""
    return ExternalLLMRouter()
