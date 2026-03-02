"""OpenAIモデルエンジンを生成するためのクラスを定義します。"""

import os
from dataclasses import dataclass

from langchain_community.chat_models import ChatOpenAI

from .base import BaseModelConfig, BaseModelFactory


@dataclass
class OpenAIConfig(BaseModelConfig):
    """OpenAIモデルの設定を定義するデータクラスです。"""

    model_name: str
    temperature: float = 0.0
    max_tokens: int = 1000


class OpenAIEngine(BaseModelFactory[OpenAIConfig]):
    """OpenAIモデルエンジンを生成するファクトリクラスです。"""

    def __init__(self, config: OpenAIConfig):
        """OpenAIエンジンの設定を初期化します。"""
        super().__init__(config)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

    def create_model_engine(self) -> ChatOpenAI:
        """指定された設定に基づいてOpenAIモデルエンジンを作成します。"""
        return ChatOpenAI(
            model_name=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
