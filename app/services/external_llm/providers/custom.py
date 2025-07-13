"""
Custom Route Provider - Handles providers defined in 'custom_model_routes'.
"""

from typing import Dict, Any
from .base import BaseProvider
from logger.logger import get_logger

logger = get_logger(__name__)


class CustomRouteProvider(BaseProvider):
    """
    Handles providers that have their full configuration (including API key
    and base URL) defined directly within the 'custom_model_routes' block
    of the configuration file.

    This provider bypasses the standard key selection and mapping logic.
    """

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        # We override __init__ because we don't need the key extraction logic
        # from the parent BaseProvider.
        self._provider_name = provider_name
        self._config = config
        self._custom_route_config = self._config.get("custom_model_routes", {}).get(
            self._provider_name
        )

        if not self._custom_route_config:
            raise ValueError(
                f"No configuration found under 'custom_model_routes' for provider '{self._provider_name}'"
            )

    def prepare_litellm_params(
        self, payload: Dict[str, Any], model_route: Any
    ) -> Dict[str, Any]:
        """
        Prepares parameters by taking all necessary info from the custom route config.
        """
        final_params = payload.copy()

        # Add api_key and base_url from the custom route config
        api_key = self._custom_route_config.get("api_key")
        base_url = self._custom_route_config.get("base_url")

        if api_key:
            final_params["api_key"] = api_key
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
