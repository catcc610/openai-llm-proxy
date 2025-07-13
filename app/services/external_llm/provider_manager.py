"""
Provider Manager (Factory) - Creates and returns provider-specific handler instances.
"""

import os
from typing import Dict, Any, Type
from logger.logger import get_logger
import time
import threading
from app.services.external_llm.providers import (
    BaseProvider,
    GenericProvider,
    CustomRouteProvider,
    BedrockProvider,
    GeminiProvider,
)

logger = get_logger(__name__)


class ProviderManager:
    """
    Acts as a factory to create the appropriate provider instance
    based on the provider name.
    """

    def __init__(self) -> None:
        self._provider_map: Dict[str, Type[BaseProvider]] = {
            "bedrock": BedrockProvider,
            "gemini": GeminiProvider,
        }
        self._default_provider = GenericProvider
        # 为每个provider维护轮询索引
        self._key_indices: Dict[str, int] = {}
        # 线程锁确保轮询索引的线程安全
        self._lock = threading.Lock()
        logger.info("✅ ProviderManager (Factory) initialized.")

    def get_provider(self, provider_name: str, config: Dict[str, Any]) -> BaseProvider:
        """
        Gets an instance of the correct provider class for the given name.
        It prioritizes custom routes if they are defined.
        """
        # 1. Check if the provider is defined in custom_model_routes first
        if provider_name in config.get("custom_model_routes", {}):
            logger.info(
                f"🏭 Found custom route for '{provider_name}'. Using CustomRouteProvider."
            )
            return CustomRouteProvider(provider_name, config, self)

        # 2. If not a custom route, use the standard provider map
        ProviderClass = self._provider_map.get(provider_name, self._default_provider)

        # Instantiate the class with its name, the global config, and this manager instance
        return ProviderClass(provider_name, config, self)

    def get_provider_config(
        self, provider: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Constructs the configuration dictionary for a given provider.
        """
        return self._get_mapped_keys(provider, config)

    def _get_next_key_index(self, provider: str, total_keys: int) -> int:
        """
        获取下一个key的索引，实现轮询逻辑
        """
        with self._lock:
            if provider not in self._key_indices:
                self._key_indices[provider] = 0

            current_index = self._key_indices[provider]
            self._key_indices[provider] = (current_index + 1) % total_keys
            return current_index

    def _get_env_value(
        self, config_value: str, provider: str, selected_key: str, env_var: str
    ) -> str:
        """
        获取环境变量的值。支持直接值和环境变量名称两种配置方式。
        """
        # 如果配置值看起来像环境变量名称（全大写，包含下划线），尝试从环境变量获取
        if config_value and config_value.isupper() and "_" in config_value:
            env_value = os.getenv(config_value)
            if env_value:
                logger.debug(f"✅ 从环境变量 '{config_value}' 获取到值")
                return env_value
            else:
                logger.warning(
                    f"⚠️ 环境变量 '{config_value}' 未找到，provider '{provider}' key '{selected_key}' 的 '{env_var}' 配置"
                )
                return ""
        else:
            # 如果不是环境变量名称格式，直接使用配置值（保持向后兼容）
            return config_value

    def _get_mapped_keys(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gets the API keys for a provider and maps them to the names
        that LiteLLM expects. 使用轮询方式选择key，支持从环境变量获取值。
        """
        provider_keys_configs = config.get("provider_keys_configs", {})
        model_keys = config.get("model_keys", {})

        key_config = provider_keys_configs.get(provider)
        if not key_config:
            logger.warning(f"⚠️ No key mapping config found for provider '{provider}'.")
            return {}

        provider_keys = model_keys.get(provider, {})
        if not provider_keys:
            logger.warning(f"⚠️ No keys found for provider '{provider}'.")
            return {}

        # 获取所有可用的key
        available_keys = [key for key in provider_keys.keys() if key.startswith("key")]
        if not available_keys:
            logger.warning(f"⚠️ No valid keys found for provider '{provider}'.")
            return {}

        # 轮询选择key
        key_index = self._get_next_key_index(provider, len(available_keys))
        selected_key = available_keys[key_index]

        provider_creds = provider_keys.get(selected_key, {})
        if not provider_creds:
            logger.warning(
                f"⚠️ No credentials found for provider '{provider}' key '{selected_key}'."
            )
            return {}

        logger.info(
            f"🔄 Provider '{provider}' using key '{selected_key}' (轮询索引: {key_index + 1}/{len(available_keys)})"
        )

        mapped_keys = {}
        env_mapping = key_config.get("env_mapping", {})

        for env_var, litellm_param in env_mapping.items():
            config_value = provider_creds.get(env_var)
            if config_value:
                # 支持从环境变量获取值
                actual_value = self._get_env_value(
                    config_value, provider, selected_key, env_var
                )
                if actual_value:
                    mapped_keys[litellm_param] = actual_value
                else:
                    logger.warning(
                        f"⚠️ 无法获取 '{env_var}' 的值，provider '{provider}' key '{selected_key}'"
                    )
            else:
                logger.warning(
                    f"⚠️ Credential variable '{env_var}' not found for provider '{provider}' key '{selected_key}'."
                )

        defaults = key_config.get("defaults", {})
        for key, value in defaults.items():
            if key not in mapped_keys:
                mapped_keys[key] = value

        return mapped_keys

    def get_all_provider_stats(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns status information for all configured providers.
        """
        stats: Dict[str, Any] = {}
        provider_keys_configs = config.get("provider_keys_configs", {})
        model_keys = config.get("model_keys", {})
        all_providers = provider_keys_configs.keys()

        for provider in all_providers:
            provider_keys = model_keys.get(provider, {})
            # 统计所有可用的key
            available_keys = [
                key for key in provider_keys.keys() if key.startswith("key")
            ]
            current_index = self._key_indices.get(provider, 0)

            stats[provider] = {
                "status": "configured" if provider_keys else "not_configured",
                "credentials_found": bool(provider_keys),
                "total_keys": len(available_keys),
                "current_key_index": current_index,
                "available_keys": available_keys,
            }

        stats["timestamp"] = int(time.time())
        return stats
