import yaml
import json
import os
from typing import Any


def get_basic_config() -> Any:
    # The script itself is in the 'config' directory.
    # Get the directory of the current script.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_config_path = os.path.join(script_dir, "basic-config.yaml")

    with open(base_config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if "routes" in config and isinstance(config["routes"], dict):
        for route_key, files in config["routes"].items():
            loaded_files_content = []
            if isinstance(files, list):
                for file_path in files:
                    # The paths in the yaml are relative to the 'config' directory
                    full_path = os.path.join(script_dir, file_path)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            if file_path.endswith((".yaml", ".yml")):
                                loaded_files_content.append(yaml.safe_load(f))
                            elif file_path.endswith(".json"):
                                loaded_files_content.append(json.load(f))
                    except FileNotFoundError:
                        # You can handle this more gracefully, e.g., logging
                        print(f"Warning: Configuration file not found at {full_path}")
                    except Exception as e:
                        print(f"Error loading configuration file {full_path}: {e}")

            # Replace file paths with their loaded content
            config["routes"][route_key] = loaded_files_content

    return config


if __name__ == "__main__":
    config = get_basic_config()
    print(config)

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

    if len(external_llm_data) < 2:
        # Handle cases where the config files might be missing or not loaded correctly.
        return {}

    # The first item is the main llm config, the second is the credential file.
    _external_llm_config = external_llm_data[0]
    vertex_ai_credential = external_llm_data[1]

    # Combine them into a single dictionary for easy use.
    # It's good practice to copy to avoid modifying the original loaded config.
    final_config = _external_llm_config.copy()
    final_config["vertex_ai_credential"] = vertex_ai_credential

    return final_config


if __name__ == "__main__":
    external_llm_config = get_external_llm_config()

    import json

    print(json.dumps(external_llm_config, indent=2, ensure_ascii=False))