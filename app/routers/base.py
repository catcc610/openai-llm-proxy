"""
基础路由抽象类
为所有 AI 服务路由提供统一的接口和基础功能
"""

from abc import ABC, abstractmethod
from fastapi import APIRouter
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class BaseRouter(ABC):
    """
    基础路由抽象类
    提供 APIRouter 实例和通用路由设置
    """

    def __init__(
        self, prefix: str = "", tags: Optional[List[Union[str, Enum]]] = None
    ) -> None:
        self.router = APIRouter(prefix=prefix, tags=tags)
        self._setup_routes()
        self._setup_common_routes()

    @abstractmethod
    def _setup_routes(self) -> None:
        """
        设置特定服务的路由。
        子类必须实现此方法。
        """
        pass

    def _setup_common_routes(self) -> None:
        """设置通用路由，如健康检查"""

        @self.router.get("/health", summary="健康检查", tags=["通用"])
        async def health_check_endpoint() -> Dict[str, Any]:
            return await self.health_check()

    async def health_check(self) -> Dict[str, Any]:
        """
        默认的健康检查实现。
        子类可以重写此方法以进行更具体的检查。
        """
        return {"status": "ok"}