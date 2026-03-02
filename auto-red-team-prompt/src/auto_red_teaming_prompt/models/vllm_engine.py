"""vLLM の REST API を使用したモデルエンジンを生成するためのクラスを定義します。"""

from dataclasses import dataclass
from typing import Optional

from langchain_openai.chat_models.base import ChatOpenAI

from .base import BaseModelConfig, BaseModelFactory


@dataclass
class VLLMConfig(BaseModelConfig):
    """VLLMモデルの設定を定義するデータクラスです。"""

    model_name: str
    openai_api_base: str
    use_reasoning: bool = True
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    min_p: Optional[float] = None
    repetition_penalty: Optional[float] = None


class VLLMEngine(BaseModelFactory[VLLMConfig]):
    """VLLMモデルエンジンを生成するファクトリクラスです。"""

    def __init__(self, config: VLLMConfig):
        """VLLMエンジンの設定を初期化します。"""
        super().__init__(config)

    def create_model_engine(self) -> ChatOpenAI:
        """指定された設定に基づいてVLLMモデルエンジンを作成します。"""
        extra_body: dict = {}
        if not self.config.use_reasoning:
            extra_body["chat_template_kwargs"] = {"enable_thinking": False}
        if self.config.temperature is not None:
            extra_body["temperature"] = self.config.temperature
        if self.config.top_p is not None:
            extra_body["top_p"] = self.config.top_p
        if self.config.top_k is not None:
            extra_body["top_k"] = self.config.top_k
        if self.config.min_p is not None:
            extra_body["min_p"] = self.config.min_p
        if self.config.repetition_penalty is not None:
            extra_body["repetition_penalty"] = self.config.repetition_penalty

        if not extra_body:
            extra_body = None  # type: ignore[assignment]

        return ChatOpenAI(
            model_name=self.config.model_name,
            openai_api_base=self.config.openai_api_base,
            openai_api_key="dummy_key",
            extra_body=extra_body,
        )
