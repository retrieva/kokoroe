"""Generator for LLM responses to red teaming prompts."""

import logging
from dataclasses import asdict
from typing import Any

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from auto_red_teaming_prompt.data import OutputPrompt, OutputResponse, load_red_prompt
from auto_red_teaming_prompt.utils.common import save_json_data
from auto_red_teaming_prompt.utils.reporter import (
    NullProgressEstimator,
    ProgressEstimator,
    ProgressReporter,
    TimeBasedProgressEstimator,
    report_with_tqdm,
)

from .base import BaseGenerator


class ResponseGenerator(
    BaseGenerator[dict[str, list[OutputPrompt]], dict[str, list[dict[str, OutputPrompt | OutputResponse]]]]
):
    """Generator for LLM responses to red teaming prompts.

    This class takes generated red teaming prompts and generates
    responses using a target LLM model.
    """

    def __init__(self, llm: BaseLanguageModel, reporter: ProgressReporter | None = None):
        """Initialize the ResponseGenerator.

        Args:
            llm: Language model to generate responses
            reporter: Optional progress reporter

        """
        super().__init__(llm, reporter)

        # Create the LLM chain for response generation
        prompt_template = PromptTemplate(input_variables=["prompt"], template="{prompt}")
        self.chain = prompt_template | self.llm | StrOutputParser()

    def generate(
        self, input_data: dict[str, list[OutputPrompt]]
    ) -> dict[str, list[dict[str, OutputPrompt | OutputResponse]]]:
        """Generate LLM responses to red teaming prompts.

        Returns:
            Dictionary mapping categories to lists of input-output pairs

        """
        output: dict[str, list[dict[str, Any]]] = {}

        total_items = sum(len(items) for items in input_data.values())
        progress_estimator: ProgressEstimator
        if isinstance(self.reporter, ProgressReporter):
            progress_estimator = TimeBasedProgressEstimator(total_items, self.reporter)
        else:
            progress_estimator = NullProgressEstimator()
        with self.reporter.ticking():
            with report_with_tqdm(
                total=total_items,
                desc="Generating responses",
                unit="response",
                logger_enabled=self.logger.isEnabledFor(logging.INFO),
                reporter=self.reporter,
            ) as pbar:
                for category, items in input_data.items():
                    output[category] = []

                    # Prepare batch input for LLM
                    llm_inputs = [{"prompt": item.prompt} for item in items]

                    self.logger.info(
                        "Generating responses for category: %s with %d prompts.",
                        category,
                        len(llm_inputs),
                        extra={"category": category, "n_prompts": len(llm_inputs)},
                    )

                    # Generate responses using batch processing
                    with progress_estimator.batch(len(llm_inputs)):
                        responses = self.chain.batch(llm_inputs)

                    # Validate response count
                    if len(responses) != len(items):
                        raise ValueError(
                            f"Expected {len(items)} responses, but got {len(responses)} for category '{category}'."
                        )

                    # Pair inputs with outputs
                    for item, response in zip(items, responses):
                        output[category].append(
                            {
                                "input": item,
                                "output": OutputResponse(
                                    response_text=response,
                                    response_status="200",
                                ),
                            }
                        )
                    pbar.update(len(items))

        return output

    def save_results(
        self, results: dict[str, list[dict[str, OutputPrompt | OutputResponse]]], output_path: str
    ) -> None:
        """Save generated responses to JSON file.

        Args:
            results: Generated responses
            output_path: Path to save the results

        """
        output_reformat = {
            category: [{"input": asdict(item["input"]), "output": asdict(item["output"])} for item in items]
            for category, items in results.items()
        }
        save_json_data(output_reformat, output_path)

    def load_data(self, input_path: str) -> dict[str, list[OutputPrompt]]:
        """Load red teaming prompts from JSON file.

        Args:
            input_path: Path to the JSON file containing red teaming prompts
        Returns:
            Dictionary mapping categories to lists of red teaming prompts

        """
        return load_red_prompt(input_path)
