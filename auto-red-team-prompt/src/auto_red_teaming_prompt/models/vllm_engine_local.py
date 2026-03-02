"""vLLM モデルをローカルで実行するための設定とファクトリクラスを定義します。"""

from dataclasses import dataclass
from typing import Optional

from langchain_community.llms.vllm import VLLM

from .base import BaseModelConfig, BaseModelFactory


@dataclass
class VLLMLocalConfig(BaseModelConfig):
    """VLLMモデルの設定を定義するデータクラスです。"""

    model_name: str
    trust_remote_code: bool = True
    max_new_tokens: int = 1000
    top_p: float = 0.95
    temperature: float = 0.0
    model_max_length: Optional[int] = None


class VLLMLocalEngine(BaseModelFactory[VLLMLocalConfig]):
    """VLLMモデルエンジンを生成するファクトリクラスです。"""

    def __init__(self, config: VLLMLocalConfig):
        """VLLMエンジンの設定を初期化します。"""
        super().__init__(config)

    def create_model_engine(self) -> VLLM:
        """指定された設定に基づいてVLLMモデルエンジンを作成します。"""
        return VLLM(
            model=self.config.model_name,
            trust_remote_code=self.config.trust_remote_code,
            max_new_tokens=self.config.max_new_tokens,
            top_p=self.config.top_p,
            temperature=self.config.temperature,
            vllm_kwargs={
                "max_model_len": self.config.model_max_length,
            },
        )
