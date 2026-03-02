"""Generator for New Constitution text based on Red Teaming results."""

import json
from dataclasses import asdict

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.base import BaseLanguageModel

from auto_red_teaming_prompt.data import (
    ConstitutionData,
    ConstitutionInput,
    SafetyClassificationQuantitativeStats,
    TargetRisk,
)
from auto_red_teaming_prompt.prompts import PROMPT_GENERATE_CONSTITUTION, constitution_parser
from auto_red_teaming_prompt.utils.reporter import ProgressReporter

from .base import BaseGenerator


class ConstitutionGenerator(BaseGenerator[ConstitutionInput, ConstitutionData]):
    """Generator for New Constitution text based on Red Teaming results."""

    NUM_RETRY = 5

    def __init__(self, llm: BaseLanguageModel, reporter: ProgressReporter | None = None):
        """Initialize the ConstitutionGenerator."""
        super().__init__(llm, reporter)

        self.chain = PROMPT_GENERATE_CONSTITUTION | self.llm | constitution_parser
        self.chain = self.chain.with_retry(
            retry_if_exception_type=(OutputParserException,),
            wait_exponential_jitter=False,
            stop_after_attempt=self.NUM_RETRY,
        )

    def generate(self, input_data: ConstitutionInput) -> ConstitutionData:
        """Generate new Constitution text based on Red Teaming results.

        Args:
            input_data: Input data containing current constitution and red teaming results.

        Returns:
            New ConstitutionData object with updated texts.

        """

        def _preprocess_constitution_texts(texts: list[str]) -> str:
            """Convert list of constitution texts to markdown list format."""
            return "\n".join(f"- {text}" for text in texts)

        def _preprocess_red_teaming_results(results: dict[str, SafetyClassificationQuantitativeStats]) -> str:
            """Convert red teaming results to a formatted string."""
            lines = []
            for category, stats in results.items():
                lines.append(f"## {category}")
                lines.append(f"- Total Attempts: {stats.number_of_attacks}")
                lines.append(f"- Successful Attacks: {stats.number_of_successes}")
                lines.append(f"- Success Rate: {stats.success_rate:.2%}")
                lines.append("")  # Add an empty line for better readability
            return "\n".join(lines)

        with self.reporter.ticking():
            self.reporter.update_progress(0.0)

            existing_constitution = _preprocess_constitution_texts(input_data["current_constitution"].texts)
            red_teaming_results = _preprocess_red_teaming_results(input_data["red_teaming_results"])

            generated_constitutions = self.chain.invoke(
                {"existing_constitution": existing_constitution, "red_teaming_results": red_teaming_results}
            )

            self.reporter.update_progress(1.0)

        return ConstitutionData(texts=generated_constitutions)

    def save_results(self, output_data: ConstitutionData, output_path: str) -> None:
        """Save the generated Constitution data to a JSON file.

        Args:
            output_data: The ConstitutionData object to save.
            output_path: The file path where the data should be saved.

        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(output_data), f, ensure_ascii=False, indent=2)

    def load_data(self, input_path: str) -> ConstitutionInput:
        """Load input data from a JSON file.

        Args:
            input_path: The file path from which to load the data.

        Returns:
            The loaded ConstitutionInput data.

        """
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        current_constitution = ConstitutionData(texts=data["llm-constitutions"])
        red_teaming_results = {
            category: SafetyClassificationQuantitativeStats(
                number_of_attacks=stats.get("number-of-attacks", stats.get("number_of_attacks")),
                number_of_successes=stats.get("number-of-successes", stats.get("number_of_successes")),
                success_rate=stats.get("success-rate", stats.get("success_rate")),
            )
            for category, stats in data["quantitative-summary"].items()
        }
        attack_scenario = [TargetRisk(**item) for item in data["attack-scenario"]]

        return ConstitutionInput(
            current_constitution=current_constitution,
            red_teaming_results=red_teaming_results,
            attack_scenario=attack_scenario,
        )
