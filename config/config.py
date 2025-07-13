from __future__ import annotations
from .basic_config import get_basic_config
from typing import Any

config = get_basic_config()


def get_config() -> Any:
    """
    Returns the entire, fully-loaded configuration dictionary.
    """
    return config


def get_server_config() -> Any:
    """
    Returns the server configuration section.
    Returns an empty dict if not found.
    """
    return config.get("server", {})


def get_routes_config() -> Any:
    """
    Returns the routes configuration section.
    Returns an empty dict if not found.
    """
    return config.get("routes", {})


def get_external_llm_config() -> Any:
    """
    Retrieves, merges, and returns the configuration for external LLMs.
    """
    routes = get_routes_config()
    external_llm_data = routes.get("external_llm", [])

    if len(external_llm_data) < 1:
        # Handle cases where the config files might be missing or not loaded correctly.
        return {}

    # The first item is the main llm config, the second is the credential file.
    _external_llm_config = external_llm_data[0]
    # vertex_ai_credential = external_llm_data[1]

    # Combine them into a single dictionary for easy use.
    # It's good practice to copy to avoid modifying the original loaded config.
    final_config = _external_llm_config.copy()
    # final_config["vertex_ai_credential"] = vertex_ai_credential

    return final_config


if __name__ == "__main__":
    external_llm_config = get_external_llm_config()

    import json

    print(json.dumps(external_llm_config, indent=2, ensure_ascii=False))
