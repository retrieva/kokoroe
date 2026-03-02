"""Abstract base class for generator-style components.

This defines a minimal, consistent interface to implement when adding a
new generator in the pipeline. Subclasses should implement ``generate``
and ``save_results`` and may add helper methods as needed.
"""

from abc import ABC, abstractmethod
from logging import Logger, getLogger
from typing import Generic, TypeVar

from langchain_core.language_models.base import BaseLanguageModel

from auto_red_teaming_prompt.utils.reporter import NullReporter, ProgressReporter

T = TypeVar("T")
R = TypeVar("R")


class BaseGenerator(ABC, Generic[T, R]):
    """Base class for generator components.

    Holds a reference to the language model and provides a module-level logger.
    """

    def __init__(self, llm: BaseLanguageModel, reporter: ProgressReporter | None) -> None:
        """Initialize the base generator with a language model.

        Args:
            llm: 言語モデルインスタンス
            reporter: 進捗の報告に使用するオブジェクト

        """
        self.llm = llm
        # Use module logger of the subclass' module
        self.logger: Logger = getLogger(self.__class__.__module__)
        self.reporter = reporter or NullReporter()

    @abstractmethod
    def generate(self, input_data: T) -> R:  # pragma: no cover - interface only
        """Run the generator and return the results."""

    @abstractmethod
    def save_results(self, results: R, output_path: str) -> None:  # pragma: no cover - interface only
        """Persist results to the given path."""
