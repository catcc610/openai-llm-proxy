"""
Generic Provider - A general-purpose provider for simple cases.
"""

from typing import Dict, Any
from .base import BaseProvider


class GenericProvider(BaseProvider):
    """
    A provider for services that don't require special parameter handling,
    just API key injection.
    """

    def prepare_litellm_params(
        self, payload: Dict[str, Any], model_route: Any
    ) -> Dict[str, Any]:
        """
        Prepares parameters by adding the selected credentials.
        The model_route is ignored here as this is a generic handler.
        """
        credentials = self.get_credentials()

        # Merge credentials into the payload
        final_params = {**payload, **credentials}

        return final_params
