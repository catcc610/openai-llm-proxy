"""
Provider Manager (Factory) - Creates and returns provider-specific handler instances.
"""

from typing import Dict, Any, Type
from logger.logger import get_logger
import time
from app.services.external_llm.providers import (
    BaseProvider,
    GenericProvider,
    CustomRouteProvider,
    BedrockProvider,
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
        }
        self._default_provider = GenericProvider
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
            return CustomRouteProvider(provider_name, config)

        # 2. If not a custom route, use the standard provider map
        ProviderClass = self._provider_map.get(provider_name, self._default_provider)

        # Instantiate the class with its name and the global config
        return ProviderClass(provider_name, config)

    def get_provider_config(
        self, provider: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Constructs the configuration dictionary for a given provider.
        """
        return self._get_mapped_keys(provider, config)

    def _get_mapped_keys(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gets the API keys for a provider and maps them to the names
        that LiteLLM expects.
        """
        provider_keys_configs = config.get("provider_keys_configs", {})
        model_keys = config.get("model_keys", {})

        key_config = provider_keys_configs.get(provider)
        if not key_config:
            logger.warning(f"⚠️ No key mapping config found for provider '{provider}'.")
            return {}

        provider_creds = model_keys.get(provider, {}).get("key1", {})
        if not provider_creds:
            logger.warning(
                f"⚠️ No credentials found for provider '{provider}' under 'key1'."
            )
            return {}

        mapped_keys = {}
        env_mapping = key_config.get("env_mapping", {})

        for env_var, litellm_param in env_mapping.items():
            value = provider_creds.get(env_var)
            if value:
                mapped_keys[litellm_param] = value
            else:
                logger.warning(
                    f"⚠️ Credential variable '{env_var}' not found for provider '{provider}'."
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
            creds = model_keys.get(provider, {}).get("key1", {})
            stats[provider] = {
                "status": "configured" if creds else "not_configured",
                "credentials_found": bool(creds),
            }

        stats["timestamp"] = int(time.time())
        return stats