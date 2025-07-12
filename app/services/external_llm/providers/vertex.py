"""
Vertex AI Provider - Specialized provider for Google Vertex AI services.
"""

from typing import Dict, Any

from .base import BaseProvider
from logger.logger import get_logger

logger = get_logger(__name__)


class VertexAIProvider(BaseProvider):
    """
    Handles the specific authentication requirements for Google Vertex AI,
    which involves reading credentials from a JSON file and handling
    model-specific location overrides.
    """

    def prepare_litellm_params(
        self, payload: Dict[str, Any], model_route: Any
    ) -> Dict[str, Any]:
        """
        Prepares parameters for Vertex AI. It reads the service account JSON,
        and intelligently merges default and model-specific configurations.
        """
        # 1. Get the base credentials, including the default location.
        credentials = self.get_credentials()

        # 2. If the model_route has a specific location, it overrides the default.
        if isinstance(model_route, dict) and "vertex_location" in model_route:
            model_specific_location = model_route.get("vertex_location")
            credentials["vertex_location"] = model_specific_location
            logger.info(
                f"🛰️ Overriding with model-specific location: '{model_specific_location}'"
            )

        # 3. Handle the JSON credentials, which are pre-loaded into the config.
        gcp_creds_json = self._config.get("vertex_ai_credential")

        if not gcp_creds_json:
            raise ValueError(
                "Vertex AI credentials ('vertex_ai_credential') not found in the application configuration."
            )

        # Ensure the loaded credentials are a dictionary
        if not isinstance(gcp_creds_json, dict):
            raise ValueError(
                f"Vertex AI credentials are not a valid dictionary/JSON object. Found type: {type(gcp_creds_json)}"
            )

        credentials["vertex_credentials"] = gcp_creds_json
        logger.info("✅ Successfully attached pre-loaded Google Cloud credentials.")

        # 4. Merge the fully prepared credentials with the rest of the payload.
        final_params = {**payload, **credentials}

        # 5. Safeguard for Vertex AI specific parameter constraints.
        # Vertex AI's Gemini models do not support top_k=0.
        # If top_k is 0, we remove it to let the API use its default.
        if final_params.get("top_k") == 0:
            del final_params["top_k"]
            logger.warning(
                "Removed 'top_k=0' from request to Vertex AI as it is not supported. "
                "The API will use its default value."
            )

        final_params["thinking"] = {"type": "enabled"}
        logger.debug("Enabled 'thinking' parameter for Vertex AI.")

        return final_params