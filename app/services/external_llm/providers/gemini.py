"""
Vertex AI Provider - Specialized provider for Google Vertex AI services.
"""

from typing import Dict, Any

from .base import BaseProvider
from logger.logger import get_logger

logger = get_logger(__name__)


class GeminiProvider(BaseProvider):
    """
    Handles the specific authentication requirements for Google Gemini,
    which involves reading credentials from a JSON file and handling
    model-specific location overrides.
    """

    def prepare_litellm_params(
        self, payload: Dict[str, Any], model_route: Any
    ) -> Dict[str, Any]:
        """
        Prepares parameters for Gemini. It reads the service account JSON,
        and intelligently merges default and model-specific configurations.
        """
        # 1. Get the base credentials, including the default location.
        credentials = self.get_credentials()

        # 4. Merge the fully prepared credentials with the rest of the payload.
        final_params = {**payload, **credentials}


        if final_params.get("top_k") == 0:
            del final_params["top_k"]
            logger.warning(
                "Removed 'top_k=0' from request to Vertex AI as it is not supported. "
                "The API will use its default value."
            )

        final_params["thinking"] = {"type": "enabled"}
        logger.debug("Enabled 'thinking' parameter for Vertex AI.")

        return final_params