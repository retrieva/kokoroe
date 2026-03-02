import json

from langchain_core.language_models.base import BaseLanguageModel

from .base import BaseModelConfig
from .openai_engine import OpenAIConfig, OpenAIEngine
from .vllm_engine import VLLMConfig, VLLMEngine
from .vllm_engine_local import VLLMLocalConfig, VLLMLocalEngine

MODELS = {
    "openai": (OpenAIConfig, OpenAIEngine),
    "vllm_local": (VLLMLocalConfig, VLLMLocalEngine),
    "vllm": (VLLMConfig, VLLMEngine),
}


def load_config_file(file_path: str, model_type: str) -> BaseModelConfig:
    """指定されたファイルからモデル設定を読み込みます。"""
    with open(file_path, "r") as file:
        config_data = json.load(file)

    if model_type not in MODELS:
        raise ValueError(f"Unsupported model type: {model_type}")
    config_class, _ = MODELS[model_type]
    return config_class(**config_data)


def get_llm(config: BaseModelConfig) -> BaseLanguageModel:
    """指定されたモデルタイプに基づいて LLM を取得します。"""
    if isinstance(config, OpenAIConfig):
        return OpenAIEngine(config).create_model_engine()
    elif isinstance(config, VLLMLocalConfig):
        return VLLMLocalEngine(config).create_model_engine()
    elif isinstance(config, VLLMConfig):
        return VLLMEngine(config).create_model_engine()
    else:
        raise ValueError(f"Unsupported model configuration: {type(config)}")
