"""Generator for evaluating LLM responses for safety classification."""

import logging
from dataclasses import asdict

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.base import BaseLanguageModel

from auto_red_teaming_prompt.data import (
    OutputPrompt,
    OutputResponse,
    Responses,
    SafetyClassificationResult,
)
from auto_red_teaming_prompt.prompts import (
    PROMPT_CLASSIFICATION_SAFETY,
    safety_classification_parser,
)
from auto_red_teaming_prompt.utils.common import load_json_data, save_json_data
from auto_red_teaming_prompt.utils.reporter import (
    NullProgressEstimator,
    ProgressEstimator,
    ProgressReporter,
    TimeBasedProgressEstimator,
    report_with_tqdm,
)

from .base import BaseGenerator


class ResponseEvaluator(
    BaseGenerator[
        dict[str, list[Responses]],
        dict[str, list[dict[str, OutputPrompt | OutputResponse | SafetyClassificationResult]]],
    ]
):
    """Generator for evaluating LLM responses for safety classification.

    This class takes generated responses and evaluates their safety
    using a classification model.
    """

    NUM_RETRY = 5

    def __init__(self, llm: BaseLanguageModel, reporter: ProgressReporter | None = None):
        """Initialize the ResponseEvaluator.

        Args:
            llm: Language model to use for evaluation
            reporter: Optional progress reporter

        """
        super().__init__(llm, reporter)

        # Create the classification chain with retry logic
        self.classification_chain = PROMPT_CLASSIFICATION_SAFETY | self.llm | safety_classification_parser
        self.classification_chain = self.classification_chain.with_retry(
            retry_if_exception_type=(OutputParserException,),
            wait_exponential_jitter=False,
            stop_after_attempt=self.NUM_RETRY,
        )

    def evaluate(
        self, input_data: dict[str, list[Responses]]
    ) -> dict[str, list[dict[str, OutputPrompt | OutputResponse | SafetyClassificationResult]]]:
        """Evaluate LLM responses for safety classification.

        Returns:
            Dictionary mapping categories to lists of evaluated results

        """
        output: dict[str, list[dict[str, OutputPrompt | OutputResponse | SafetyClassificationResult]]] = {}

        total_items = sum(len(items) for items in input_data.values())
        progress_estimator: ProgressEstimator
        if isinstance(self.reporter, ProgressReporter):
            progress_estimator = TimeBasedProgressEstimator(total_items, self.reporter)
        else:
            progress_estimator = NullProgressEstimator()
        with self.reporter.ticking():
            with report_with_tqdm(
                total=total_items,
                desc="Overall Evaluation Progress",
                unit="item",
                logger_enabled=self.logger.isEnabledFor(logging.INFO),
                reporter=self.reporter,
            ) as pbar:
                for category, items in input_data.items():
                    output[category] = []

                    # Prepare batch inputs for classification
                    batched_inputs = []
                    for item in items:
                        prompt: OutputPrompt = item["input"]
                        response: OutputResponse = item["output"]

                        batched_inputs.append({"prompt": prompt.prompt, "response": response.response_text})

                    self.logger.info(
                        "Processing category: %s, number of items: %d",
                        category,
                        len(batched_inputs),
                        extra={"category": category, "n_items": len(batched_inputs)},
                    )

                    # Run safety classification
                    with progress_estimator.batch(len(batched_inputs)):
                        classification_outputs: list[str] = self.classification_chain.batch(batched_inputs)

                    # Validate output count
                    if len(classification_outputs) != len(items):
                        raise ValueError(
                            f"Expected {len(items)} classification results, "
                            f"but got {len(classification_outputs)} for category '{category}'."
                        )

                    # Combine inputs, outputs, and classifications
                    for item, classification in zip(items, classification_outputs):
                        output[category].append(
                            {
                                "input": item["input"],
                                "output": item["output"],
                                "classification": SafetyClassificationResult(
                                    classification_label=classification,
                                ),
                            }
                        )
                    pbar.update(len(items))

        return output

    # Base interface unification: provide generate() as an alias
    def generate(
        self, input_data: dict[str, list[Responses]]
    ) -> dict[str, list[dict[str, OutputPrompt | OutputResponse | SafetyClassificationResult]]]:
        """Alias of evaluate() to conform to BaseGenerator interface."""
        return self.evaluate(input_data)

    def save_results(
        self,
        results: dict[str, list[dict[str, OutputPrompt | OutputResponse | SafetyClassificationResult]]],
        output_path: str,
    ) -> None:
        """Save evaluation results to JSON file.

        Args:
            results: Evaluation results
            output_path: Path to save the results

        """
        output_reformat = {
            category: [
                {
                    "input": asdict(item["input"]),
                    "output": asdict(item["output"]),
                    "classification": asdict(item["classification"]),
                }
                for item in items
            ]
            for category, items in results.items()
        }
        save_json_data(output_reformat, output_path)

    def load_data(self, evaluation_file: str) -> dict[str, list[Responses]]:
        """Load evaluation data from a specified JSON file.

        Args:
            evaluation_file: Path to the JSON file containing evaluation data

        Returns:
            Dictionary mapping categories to lists of input-output pairs

        """
        data = load_json_data(evaluation_file)

        # Convert to internal format
        formatted_data: dict[str, list[Responses]] = {}
        for category, items in data.items():
            formatted_data[category] = [
                Responses(input=OutputPrompt(**item["input"]), output=OutputResponse(**item["output"]))
                for item in items
            ]

        return formatted_data
