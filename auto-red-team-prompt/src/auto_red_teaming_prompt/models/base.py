"""BaseModelConfigとBaseModelFactoryの抽象クラスを定義します。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from langchain_core.language_models.base import BaseLanguageModel

C = TypeVar("C", bound="BaseModelConfig")


@dataclass
class BaseModelConfig(ABC):
    """基本モデルの設定を定義する抽象クラスです。"""

    pass


class BaseModelFactory(Generic[C], ABC):
    """基本モデルファクトリの抽象クラスです。"""

    def __init__(self, config: C):
        """モデルエンジンの設定を初期化します。"""
        self.config = config

    @abstractmethod
    def create_model_engine(self) -> BaseLanguageModel:
        """指定された設定に基づいてモデルエンジンを作成します。"""
        pass
