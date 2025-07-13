"""
Custom Route Provider - Handles providers defined in 'custom_model_routes'.
"""

import os
from typing import Dict, Any, Optional
from .base import BaseProvider
from logger.logger import get_logger

logger = get_logger(__name__)


class CustomRouteProvider(BaseProvider):
    """
    Handles providers that have their full configuration (including API key
    and base URL) defined directly within the 'custom_model_routes' block
    of the configuration file.

    This provider now supports environment variables for API keys.
    """

    def __init__(
        self,
        provider_name: str,
        config: Dict[str, Any],
        provider_manager: Optional[Any] = None,
    ):
        # We override __init__ because we don't need the key extraction logic
        # from the parent BaseProvider.
        self._provider_name = provider_name
        self._config = config
        self._custom_route_config = self._config.get("custom_model_routes", {}).get(
            self._provider_name
        )

        # 使用传入的ProviderManager实例，如果没有传入则创建新实例
        if provider_manager is not None:
            self._provider_manager = provider_manager
        else:
            # 导入ProviderManager来使用轮询机制
            from app.services.external_llm.provider_manager import ProviderManager

            self._provider_manager = ProviderManager()

        if not self._custom_route_config:
            raise ValueError(
                f"No configuration found under 'custom_model_routes' for provider '{self._provider_name}'"
            )

    def _get_env_value(self, config_value: str) -> str:
        """
        获取环境变量的值。支持直接值和环境变量名称两种配置方式。
        """
        # 如果配置值看起来像环境变量名称（全大写，包含下划线），尝试从环境变量获取
        if config_value and config_value.isupper() and "_" in config_value:
            env_value = os.getenv(config_value)
            if env_value:
                logger.debug(
                    f"✅ 从环境变量 '{config_value}' 获取到值用于自定义路由 '{self._provider_name}'"
                )
                return env_value
            else:
                logger.warning(
                    f"⚠️ 环境变量 '{config_value}' 未找到，自定义路由 '{self._provider_name}' 配置"
                )
                return ""
        else:
            # 如果不是环境变量名称格式，直接使用配置值（保持向后兼容）
            return config_value

    def prepare_litellm_params(
        self, payload: Dict[str, Any], model_route: Any
    ) -> Dict[str, Any]:
        """
        Prepares parameters by taking all necessary info from the custom route config.
        Now supports environment variables for API keys.
        """
        final_params = payload.copy()

        # Add api_key and base_url from the custom route config
        api_key_config = self._custom_route_config.get("api_key")
        base_url = self._custom_route_config.get("base_url")

        if api_key_config:
            # 支持从环境变量获取API key
            actual_api_key = self._get_env_value(api_key_config)
            if actual_api_key:
                final_params["api_key"] = actual_api_key
            else:
                logger.warning(
                    f"⚠️ 无法获取自定义路由 '{self._provider_name}' 的API key"
                )

        if base_url:
            final_params["base_url"] = base_url

        # For custom OpenAI-compatible endpoints, we must replace any incoming
        # provider prefix with 'openai/'.
        # 1. Get the model name from the payload, which might be prefixed.
        model_name_from_payload = payload.get("model")

        # 2. Strip any existing prefix to get the base model name.
        if model_name_from_payload:
            base_model_name = model_name_from_payload.split("/")[-1]
        else:
            # Handle the case where model is not in payload, though it should be.
            # Depending on strictness, could raise an error here.
            base_model_name = ""

        # 3. Look up the final model name in the custom route config.
        final_model_name = self._custom_route_config.get(
            base_model_name, base_model_name
        )

        # 4. Set the final model ID with the required 'openai/' prefix.
        final_params["model"] = f"openai/{final_model_name}"

        logger.info(
            f"Using custom route for '{self._provider_name}'. Final model: '{final_params['model']}'"
        )
        return final_params
