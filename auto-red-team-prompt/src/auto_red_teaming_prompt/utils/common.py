"""Common utility functions for auto red teaming prompt generation."""

import json
from pathlib import Path
from typing import Any

from langchain_core.language_models.base import BaseLanguageModel

from auto_red_teaming_prompt.models import get_llm, load_config_file


def initialize_llm(model_type: str, config_file: str) -> BaseLanguageModel:
    """Initialize language model with configuration.

    Args:
        model_type: Type of language model (e.g., 'openai', 'vllm')
        config_file: Path to model configuration file

    Returns:
        Initialized language model

    """
    config = load_config_file(config_file, model_type)
    return get_llm(config)


def load_json_data(file_path: str) -> dict[str, Any]:
    """Load data from JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Loaded JSON data

    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_data(data: dict[str, Any], file_path: str) -> None:
    """Save data to JSON file.

    Args:
        data: Data to save
        file_path: Path to save the file

    """
    # Create parent directory if it doesn't exist
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
