"""
基础服务抽象类
为所有 AI 服务提供统一的接口和基础功能
"""

from abc import ABC
from typing import Any, Dict, Optional
from logger.logger import get_logger

logger = get_logger(__name__)


class ServiceError(Exception):
    """服务错误基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class BaseService(ABC):
    """
    基础服务抽象类
    """

    def __init__(
        self, service_name: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        self.service_name = service_name
        self.config = config or {}

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取服务健康状态。
        子类可以重写此方法以提供更详细的状态信息。
        """
        return {
            "service": self.service_name,
            "status": "healthy",
            "config_loaded": bool(self.config),
        }

    def log_request(
        self, request_id: str, action: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录请求日志"""
        logger.info(f"[{request_id}] {action}: {details or {}}")

    def log_error(
        self,
        request_id: str,
        error: Exception,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录错误日志"""
        logger.error(f"[{request_id}] Error: {str(error)}, Details: {details or {}}")


class ServiceRegistry:
    """服务注册表"""

    _services: Dict[str, BaseService] = {}

    @classmethod
    def register(cls, service_name: str, instance: BaseService) -> None:
        """注册服务"""
        cls._services[service_name] = instance
        logger.info(f"✅ 服务已注册: {service_name}")

    @classmethod
    def get_service(cls, service_name: str) -> Optional[BaseService]:
        """获取服务"""
        return cls._services.get(service_name)

    @classmethod
    def list_services(cls) -> list[str]:
        """列出所有服务"""
        return list(cls._services.keys())

    @classmethod
    def get_all_services(cls) -> Dict[str, BaseService]:
        """获取所有服务"""
        return cls._services.copy()