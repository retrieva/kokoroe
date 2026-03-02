"""Improve the response based on the constitution."""

import logging
from dataclasses import asdict

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.base import BaseLanguageModel

from auto_red_teaming_prompt.data import (
    ConstitutionData,
    OutputPrompt,
    OutputResponse,
    ResponseImproverInput,
    Responses,
)
from auto_red_teaming_prompt.prompts import PROMPT_RESPONSE_IMPROVE, response_improvement_parser
from auto_red_teaming_prompt.utils import load_json_data, save_json_data
from auto_red_teaming_prompt.utils.reporter import (
    NullProgressEstimator,
    ProgressEstimator,
    ProgressReporter,
    TimeBasedProgressEstimator,
    report_with_tqdm,
)

from .base import BaseGenerator


class ResponseImprover(BaseGenerator[ResponseImproverInput, dict[str, list[dict[str, OutputPrompt | OutputResponse]]]]):
    """Improve the response based on the constitution."""

    NUM_RETRY = 5

    def __init__(self, llm: BaseLanguageModel, reporter: ProgressReporter | None = None):
        """Initialize the ResponseImprover.

        Args:
            llm: Language model to improve responses
            reporter: Optional progress reporter

        """
        super().__init__(llm, reporter)

        # Create the LLM chain for response improvement
        self.chain = PROMPT_RESPONSE_IMPROVE | self.llm | response_improvement_parser
        self.chain = self.chain.with_retry(
            retry_if_exception_type=(OutputParserException,),
            wait_exponential_jitter=False,
            stop_after_attempt=self.NUM_RETRY,
        )

    def generate(self, input_data: ResponseImproverInput) -> dict[str, list[dict[str, OutputPrompt | OutputResponse]]]:
        """Improve the response based on the constitution.

        Returns:
            Dictionary mapping categories to lists of improved input-output pairs

        """
        output: dict[str, list[dict[str, OutputPrompt | OutputResponse]]] = {}

        original_responses = input_data.responses
        # constitution texts in markdown list format
        constitution_texts = "\n".join(f"- {text}" for text in input_data.constitution.texts)
        total_items = sum(len(items) for items in original_responses.values())
        progress_estimator: ProgressEstimator
        if isinstance(self.reporter, ProgressReporter):
            progress_estimator = TimeBasedProgressEstimator(total_items, self.reporter)
        else:
            progress_estimator = NullProgressEstimator()
        with self.reporter.ticking():
            with report_with_tqdm(
                total=total_items,
                desc="Improving responses",
                unit="response",
                logger_enabled=self.logger.isEnabledFor(logging.INFO),
                reporter=self.reporter,
            ) as pbar:
                for category, items in original_responses.items():
                    output[category] = []

                    # Prepare batch input for LLM
                    llm_inputs = [
                        {
                            "prompt": item["input"].prompt,
                            "response": item["output"].response_text,
                            "constitution": constitution_texts,
                        }
                        for item in items
                    ]

                    # Generate improved responses in batch
                    with progress_estimator.batch(len(llm_inputs)):
                        improved_responses = self.chain.batch(llm_inputs)

                    if len(improved_responses) != len(items):
                        raise ValueError(
                            f"Expected {len(items)} improved responses, but got {len(improved_responses)} for category '{category}'."
                        )
                    for item, improved_response in zip(items, improved_responses):
                        output[category].append(
                            {
                                "input": item["input"],
                                "output": item["output"],
                                "improved_response": OutputResponse(
                                    response_text=improved_response, response_status="200"
                                ),
                            }
                        )
                    pbar.update(len(items))

        return output

    def load_data(self, response_file: str, constitution_file: str) -> ResponseImproverInput:
        """Load input data from JSON files.

        Args:
            response_file: Path to the JSON file containing generated responses.
            constitution_file: Path to the Constitution file (text format).

        Returns:
            Input data for the ResponseImprover.

        """
        # Load generated responses
        responses = load_json_data(response_file)
        formatted_responses: dict[str, list[Responses]] = {}
        for category, items in responses.items():
            formatted_responses[category] = []
            for item in items:
                formatted_responses[category].append(
                    Responses(input=OutputPrompt(**item["input"]), output=OutputResponse(**item["output"]))
                )
        # Load constitution text
        constitution_data = load_json_data(constitution_file)
        formatted_constitution = ConstitutionData(**constitution_data)

        return ResponseImproverInput(responses=formatted_responses, constitution=formatted_constitution)

    def save_results(
        self,
        results: dict[str, list[dict[str, OutputPrompt | OutputResponse]]],
        output_path: str,
    ) -> None:
        """Save improved responses to JSON file.

        Args:
            results: Improved responses
            output_path: Path to save the results

        """
        output_reformat = {
            category: [
                {
                    "input": asdict(item["input"]),
                    "output": asdict(item["output"]),
                    "improved_response": asdict(item["improved_response"]),
                }
                for item in items
            ]
            for category, items in results.items()
        }

        save_json_data(output_reformat, output_path)
