"""
Bedrock Provider
"""

from typing import Dict, Any
from .base import BaseProvider
from logger.logger import get_logger

logger = get_logger(__name__)


class BedrockProvider(BaseProvider):
    """
    Provider for AWS Bedrock models.
    It filters out unsupported parameters before sending the request to LiteLLM.
    """

    def prepare_litellm_params(
        self, payload: Dict[str, Any], model_route: Any
    ) -> Dict[str, Any]:
        """
        Prepares the request for Bedrock by adding credentials and filtering
        out unsupported parameters.

        Unsupported parameters to be removed:
        - top_k
        - min_p
        - repetition_penalty
        - top_a
        - frequency_penalty
        - presence_penalty
        """
        # Get credentials and common parameters
        litellm_params = self.get_credentials()

        # Update with the original payload
        litellm_params.update(payload)

        # List of unsupported parameters for Bedrock
        unsupported_params = [
            "top_k",
            "min_p",
            "repetition_penalty",
            "top_a",
            "frequency_penalty",
            "presence_penalty",
        ]

        # Filter out unsupported parameters
        filtered_params = {
            key: value
            for key, value in litellm_params.items()
            if key not in unsupported_params
        }

        # Log removed parameters for debugging
        removed_keys = set(litellm_params.keys()) - set(filtered_params.keys())
        if removed_keys:
            logger.debug(
                f"Removed unsupported Bedrock params: {', '.join(removed_keys)}"
            )

        return filtered_params