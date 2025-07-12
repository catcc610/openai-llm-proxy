"""
Base Provider - Abstract base class for all LLM providers.
"""

import abc
import random
from typing import Dict, Any, List

from logger.logger import get_logger

logger = get_logger(__name__)


class BaseProvider(abc.ABC):
    """
    Abstract base class for all LLM providers.
    It handles common tasks like key selection and provides a standard
    interface for preparing request parameters.
    """

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        self._provider_name = provider_name
        self._config = config
        self._keys = self._extract_keys()

    def _extract_keys(self) -> List[Dict[str, Any]]:
        """Extracts all available keys (key1, key2, etc.) for this provider."""
        provider_key_data = self._config.get("model_keys", {}).get(
            self._provider_name, {}
        )
        if not provider_key_data:
            logger.warning(
                f"⚠️ No keys found for provider '{self._provider_name}' in config."
            )
            return []
        return [v for k, v in provider_key_data.items() if k.startswith("key")]

    def _select_key(self) -> Dict[str, Any]:
        """Randomly selects one of the available API keys."""
        if not self._keys:
            raise ValueError(
                f"No API keys configured for provider: {self._provider_name}"
            )
        selected_key_group = random.choice(self._keys)
        return selected_key_group

    def get_credentials(self) -> Dict[str, Any]:
        """
        Selects a key and maps it to the format LiteLLM expects,
        including any default parameters for the provider.
        """
        key_group = self._select_key()
        key_mapping_config = self._config.get("provider_keys_configs", {}).get(
            self._provider_name
        )

        if not key_mapping_config:
            raise ValueError(
                f"No key mapping configuration for provider: {self._provider_name}"
            )

        mapped_creds = {}

        # 1. Process environment variable mappings from the selected key group
        env_mapping = key_mapping_config.get("env_mapping", {})
        for env_var, litellm_param in env_mapping.items():
            if env_var in key_group:
                mapped_creds[litellm_param] = key_group[env_var]

        # 2. Add default values from the provider's config
        defaults = key_mapping_config.get("defaults", {})
        for key, value in defaults.items():
            # Only add the default value if it hasn't been provided in the specific key group
            if key not in mapped_creds:
                mapped_creds[key] = value

        return mapped_creds

    @abc.abstractmethod
    def prepare_litellm_params(
        self, payload: Dict[str, Any], model_route: Any
    ) -> Dict[str, Any]:
        """
        Prepares the final dictionary of parameters to be passed to LiteLLM.
        Subclasses must implement this to add provider-specific logic.

        Args:
            payload: The base request payload.
            model_route: The resolved route info from config (can be str or dict).
        """
        pass