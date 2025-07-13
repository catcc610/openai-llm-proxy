"""
Model Router - a dedicated module for model routing logic.
"""

from __future__ import annotations
from typing import Dict, Any
from logger.logger import get_logger

logger = get_logger(__name__)


def get_provider_from_model(model_name: str, config: Dict[str, Any]) -> Any:
    """
    Retrieves the provider for a given model name.
    It handles standard names (e.g., 'gpt-4o') and prefixed names (e.g., 'openai/gpt-4o').
    """
    provider_config = config.get("provider_config", {})

    # 1. Try a direct match with the full model name
    provider = provider_config.get(model_name)
    if provider:
        return provider

    # 2. If no direct match, and there's a '/', try the part after the '/'
    if "/" in model_name:
        base_model_name = model_name.split("/", 1)[1]
        provider = provider_config.get(base_model_name)
        if provider:
            logger.debug(
                f"Found provider '{provider}' for base model '{base_model_name}' from full model '{model_name}'."
            )
            return provider

    # 3. If still not found, log a warning and default to 'unknown'
    logger.warning(
        f"⚠️ Provider for model '{model_name}' not found. Defaulting to 'unknown'."
    )
    return "unknown"


def resolve_model(model_name: str, config: Dict[str, Any]) -> Any:
    """
    Resolves the actual model identifier to be used by LiteLLM.
    This can be a simple string or a dictionary for complex cases like Vertex AI.
    """
    provider = get_provider_from_model(model_name, config)

    # Check for custom model routes first
    if provider in config.get("custom_model_routes", {}):
        custom_route_config = config["custom_model_routes"][provider]
        if model_name in custom_route_config:
            # For custom routes, the key in the config IS the model identifier.
            # We should not be adding any prefixes. LiteLLM needs the model to be
            # prefixed with 'openai/' for custom OpenAI-compatible endpoints,
            # so the key in the config should already be, e.g., 'openai/gpt-4o'.
            logger.debug(f"Resolved model '{model_name}' from custom route.")
            return model_name

    # Check standard model routes
    if provider in config.get("model_routes", {}):
        provider_routes = config["model_routes"][provider]
        resolved_name = provider_routes.get(model_name, model_name)
        return resolved_name

    logger.warning(
        f"⚠️ No specific route found for model '{model_name}'. Using the model name directly."
    )
    return model_name
