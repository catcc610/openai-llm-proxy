"""
Base Provider - Abstract base class for all LLM providers.
"""

import abc
import random
from typing import Dict, Any, List, Optional

from logger.logger import get_logger

logger = get_logger(__name__)


class BaseProvider(abc.ABC):
    """
    Abstract base class for all LLM providers.
    It handles common tasks like key selection and provides a standard
    interface for preparing request parameters.
    """

    def __init__(
        self,
        provider_name: str,
        config: Dict[str, Any],
        provider_manager: Optional[Any] = None,
    ):
        self._provider_name = provider_name
        self._config = config
        self._keys = self._extract_keys()
        # 使用传入的ProviderManager实例，如果没有传入则创建新实例
        if provider_manager is not None:
            self._provider_manager = provider_manager
        else:
            # 导入ProviderManager来使用轮询机制
            from app.services.external_llm.provider_manager import ProviderManager

            self._provider_manager = ProviderManager()

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
        使用ProviderManager的轮询机制选择key。
        """
        # 使用ProviderManager的轮询机制获取credentials
        return self._provider_manager._get_mapped_keys(  # type: ignore[no-any-return]
            self._provider_name, self._config
        )

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
