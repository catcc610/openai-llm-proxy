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
