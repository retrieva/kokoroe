"""Generator for safety classification summaries."""

import random
from dataclasses import asdict
from typing import TypedDict

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser

from auto_red_teaming_prompt.data import (
    OutputPrompt,
    OutputResponse,
    SafetyClassificationQualitativeStats,
    SafetyClassificationQuantitativeStats,
    SafetyClassificationResult,
)
from auto_red_teaming_prompt.prompts import PROMPT_RED_TEAMING_SUMMARY
from auto_red_teaming_prompt.utils.common import load_json_data, save_json_data
from auto_red_teaming_prompt.utils.reporter import ProgressReporter

from .base import BaseGenerator


class SafetySummarizerInput(TypedDict):
    """TypedDict for input data to SafetySummarizer."""

    input: OutputPrompt
    output: OutputResponse
    classification: SafetyClassificationResult


class SafetySummarizer(
    BaseGenerator[
        dict[str, list[SafetySummarizerInput]],
        dict[str, str | dict[str, dict]],
    ]
):
    """Generator for safety classification summaries.

    This class takes safety classification results and generates
    both quantitative and qualitative summaries with LLM-generated insights.
    """

    def __init__(self, llm: BaseLanguageModel, num_max_samples: int = 2, reporter: ProgressReporter | None = None):
        """Initialize the SafetySummarizer.

        Args:
            llm: Language model to use for summary generation
            num_max_samples: Maximum number of examples to sample
            reporter: ProgressReporter for reporting progress

        """
        super().__init__(llm, reporter)
        self.num_max_samples = num_max_samples

        # Create the summarization chain
        self.summarizer = PROMPT_RED_TEAMING_SUMMARY | self.llm | StrOutputParser()

    def generate_summary(self, input_data: dict[str, list[SafetySummarizerInput]]) -> dict[str, str | dict[str, dict]]:
        """Generate safety classification summary.

        Returns:
            Dictionary containing overall summary and aggregated statistics

        """
        with self.reporter.ticking():
            self.reporter.update_progress(0.0)
            # Generate quantitative and qualitative summaries
            quantitative_summary = self._aggregate_quantitative_data(input_data)
            qualitative_summary = self._aggregate_qualitative_data(input_data)

            # Generate overall summary using LLM
            overall_summary = self._generate_overall_summary(quantitative_summary)

            self.reporter.update_progress(1.0)

        result: dict[str, str | dict[str, dict]] = {
            "overall-summary": overall_summary,
            "quantitative-summary": {k: asdict(v) for k, v in quantitative_summary.items()},
            "qualitative-summary": {k: asdict(v) for k, v in qualitative_summary.items()},
        }
        self.logger.info("Built summary for %d categories", len(input_data), extra={"n_categories": len(input_data)})
        return result

    # Base interface unification
    def generate(self, input_data: dict[str, list[SafetySummarizerInput]]) -> dict[str, str | dict[str, dict]]:
        """Alias to generate_summary() to conform to BaseGenerator interface."""
        return self.generate_summary(input_data)

    def load_data(self, input_file: str) -> dict[str, list[SafetySummarizerInput]]:
        """Load safety classification data from JSON file.

        Returns:
            Dictionary mapping categories to lists of classified results

        """
        data = load_json_data(input_file)

        # Convert to internal format
        formatted_data: dict[str, list[SafetySummarizerInput]] = {}
        for category, items in data.items():
            formatted_data[category] = [
                {
                    "input": OutputPrompt(**item["input"]),
                    "output": OutputResponse(**item["output"]),
                    "classification": SafetyClassificationResult(**item["classification"]),
                }
                for item in items
            ]

        return formatted_data

    def _aggregate_quantitative_data(
        self, data: dict[str, list[SafetySummarizerInput]]
    ) -> dict[str, SafetyClassificationQuantitativeStats]:
        """Aggregate quantitative statistics.

        Args:
            data: Categorized classification results

        Returns:
            Dictionary mapping categories to quantitative statistics

        """
        summary: dict[str, SafetyClassificationQuantitativeStats] = {}

        for category, items in data.items():
            stats = {"number_of_successes": 0, "number_of_attacks": 0}

            for item in items:
                classification: SafetyClassificationResult = item["classification"]
                if classification.classification_label == "unsafe":
                    stats["number_of_successes"] += 1
                stats["number_of_attacks"] += 1

            success_rate = (
                stats["number_of_successes"] / stats["number_of_attacks"] if stats["number_of_attacks"] > 0 else 0.0
            )

            summary[category] = SafetyClassificationQuantitativeStats(
                number_of_successes=stats["number_of_successes"],
                number_of_attacks=stats["number_of_attacks"],
                success_rate=success_rate,
            )

        return summary

    def _aggregate_qualitative_data(
        self, data: dict[str, list[SafetySummarizerInput]]
    ) -> dict[str, SafetyClassificationQualitativeStats]:
        """Aggregate qualitative examples.

        Args:
            data: Categorized classification results

        Returns:
            Dictionary mapping categories to qualitative statistics

        """
        summary: dict[str, SafetyClassificationQualitativeStats] = {}

        for category, items in data.items():
            attack_success_examples = []
            guard_success_examples = []

            for item in items:
                classification: SafetyClassificationResult = item["classification"]
                prompt: OutputPrompt = item["input"]
                response: OutputResponse = item["output"]

                example: dict[str, str] = {
                    "prompt": prompt.prompt,
                    "response": response.response_text or "",
                    "raw_data": str(response.optional_data or {}),
                }

                if classification.classification_label == "unsafe":
                    attack_success_examples.append(example)
                elif classification.classification_label == "safe":
                    guard_success_examples.append(example)

            # Randomly sample examples
            random.shuffle(attack_success_examples)
            random.shuffle(guard_success_examples)

            if self.num_max_samples == -1:
                summary[category] = SafetyClassificationQualitativeStats(
                    attack_success_examples=attack_success_examples,
                    guard_success_examples=guard_success_examples,
                )
            else:
                summary[category] = SafetyClassificationQualitativeStats(
                    attack_success_examples=attack_success_examples[: self.num_max_samples],
                    guard_success_examples=guard_success_examples[: self.num_max_samples],
                )

        return summary

    def _generate_overall_summary(self, quantitative_summary: dict[str, SafetyClassificationQuantitativeStats]) -> str:
        """Generate overall summary using LLM.

        Args:
            quantitative_summary: Quantitative statistics by category

        Returns:
            LLM-generated overall summary

        """
        quantitative_summary_text = self._build_quantitative_summary_text(quantitative_summary)

        return self.summarizer.invoke(
            {
                "quantitative_stats": quantitative_summary_text,
            }
        )

    def _build_quantitative_summary_text(
        self, quantitative_data: dict[str, SafetyClassificationQuantitativeStats]
    ) -> str:
        """Build formatted text for quantitative summary.

        Args:
            quantitative_data: Quantitative statistics

        Returns:
            Formatted summary text

        """
        summary_text = "### Quantitative Summary\n"
        for category, stats in quantitative_data.items():
            summary_text += (
                f"- **{category}**: {stats.number_of_successes} successes out of "
                f"{stats.number_of_attacks} attacks (Success Rate: {stats.success_rate:.2%})\n"
            )
        return summary_text

    def save_results(self, results: dict[str, str | dict[str, dict]], output_path: str) -> None:
        """Save summary results to JSON file.

        Args:
            results: Summary results
            output_path: Path to save the results

        """
        save_json_data(results, output_path)
