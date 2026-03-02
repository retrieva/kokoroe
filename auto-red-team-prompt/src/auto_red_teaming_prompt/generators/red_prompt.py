"""Generator for red teaming prompts."""

import logging
from collections import defaultdict
from dataclasses import asdict
from typing import Optional, cast

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.base import BaseLanguageModel
from tqdm import tqdm

from auto_red_teaming_prompt.data import (
    LengthLimit,
    OutputPrompt,
    TargetRisk,
    load_risk,
)
from auto_red_teaming_prompt.prompts import (
    PROMPT_ENTITY,
    PROMPT_GENERATE_RED_PROMPT,
    PROMPT_GENERATE_RED_PROMPT_SCENARIO,
    PROMPT_GENERATE_RED_PROMPT_SCENARIO_WITH_LENGTH,
    PROMPT_GENERATE_RED_PROMPT_WITH_LENGTH,
    PROMPT_SCENARIO,
    DetailAttackScenarioFormat,
    EntityFormat,
    GeneratedPromptFormat,
    entity_parser,
    generate_red_prompt_parser,
    scenario_parser,
)
from auto_red_teaming_prompt.tools import web_search_and_summarize
from auto_red_teaming_prompt.utils.common import save_json_data
from auto_red_teaming_prompt.utils.reporter import (
    NullProgressEstimator,
    ProgressEstimator,
    ProgressReporter,
    TimeBasedProgressEstimator,
    report_with_tqdm,
)

from .base import BaseGenerator


class RedPromptGenerator(
    BaseGenerator[tuple[list[TargetRisk], Optional[list[LengthLimit]]], dict[str, list[OutputPrompt]]]
):
    """Generator for red teaming prompts.

    This class generates adversarial prompts based on risk categories,
    entities, and attack scenarios.
    """

    NUM_RETRY = {
        "entity": 10,
        "scenario": 10,
        "question": 10,
    }

    def __init__(
        self,
        llm: BaseLanguageModel,
        use_web_search: bool = False,
        length_pool: list[LengthLimit] | None = None,
        severity_amplify_entity: int = 5,
        severity_amplify_scenario: int = 2,
        reporter: ProgressReporter | None = None,
    ):
        """Initialize the RedPromptGenerator.

        Args:
            llm: Language model to use for generation
            risk_json: Path to risk data JSON file
            use_web_search: Whether to use web search for entity enrichment
            length_pool: Optional length limits for generated prompts
            severity_amplify_entity: Amplification factor for number of entities based on severity
            severity_amplify_scenario: Amplification factor for number of scenarios based on severity
            reporter: Optional progress reporter

        """
        super().__init__(llm, reporter)
        self.use_web_search = use_web_search
        self.length_pool = length_pool
        self.severity_amplify_factor_for_entity = severity_amplify_entity
        self.severity_amplify_factor_for_scenario = severity_amplify_scenario

    def generate(
        self, input_data: tuple[list[TargetRisk], Optional[list[LengthLimit]]]
    ) -> dict[str, list[OutputPrompt]]:
        """Generate red teaming prompts.

        Returns:
            Dictionary mapping categories to lists of output prompts

        """
        target_risks, length_pool = input_data
        if length_pool:
            self.length_pool = length_pool

        self.logger.info("Loaded %d target risks", len(target_risks))

        output: dict[str, list[OutputPrompt]] = defaultdict(list)
        total_prompts = 0
        for risk in target_risks:
            total_prompts += self._estimate_prompt_count(risk)
        # progress estimator は prompt 単位で進める
        progress_estimator: ProgressEstimator
        if isinstance(self.reporter, ProgressReporter):
            progress_estimator = TimeBasedProgressEstimator(total_prompts, self.reporter)
        else:
            progress_estimator = NullProgressEstimator()

        with self.reporter.ticking():
            with report_with_tqdm(
                total=total_prompts,
                desc="Generating prompts for all risks",
                unit="prompt",
                logger_enabled=self.logger.isEnabledFor(logging.INFO),
                reporter=self.reporter,
            ) as pbar:
                for target_risk in target_risks:
                    self.logger.info(
                        "Generating prompts for category: %s",
                        target_risk.category,
                        extra={"category": target_risk.category},
                    )
                    estimated_count_for_risk = self._estimate_prompt_count(target_risk)
                    with progress_estimator.batch(estimated_count_for_risk):
                        prompts = self._generate_prompts_for_risk(target_risk)
                    output[target_risk.category].extend(prompts)
                    pbar.update(len(prompts))

        return dict(output)

    def save_results(self, results: dict[str, list[OutputPrompt]], output_path: str) -> None:
        """Save generated prompts to JSON file.

        Args:
            results: Generated prompts
            output_path: Path to save the results

        """
        output_reformat = {category: [asdict(item) for item in items] for category, items in results.items()}
        save_json_data(output_reformat, output_path)

    def _generate_prompts_for_risk(self, target_risk: TargetRisk) -> list[OutputPrompt]:
        """Generate prompts for a single risk.

        Args:
            target_risk: Target risk to generate prompts.

        Returns:
            List of generated prompts

        """
        prompts = []

        # Generate entities and their summaries
        entities, summaries = self._generate_entities(target_risk)

        # Generate scenarios
        scenarios = self._generate_scenarios(target_risk)

        # Generate entity-based prompts
        entity_prompts = self._generate_entity_prompts(target_risk, entities, summaries)
        prompts.extend(entity_prompts)

        # Generate scenario-based prompts
        scenario_prompts = self._generate_scenario_prompts(target_risk, scenarios)
        prompts.extend(scenario_prompts)

        return prompts

    def _generate_entities(self, target_risk: TargetRisk) -> tuple[list[str], list[str]]:
        """Generate entities and their summaries.

        Args:
            target_risk: Target risk to generate entities for

        Returns:
            Tuple of entities and their summaries

        """
        severity = target_risk.severity
        n_entity = max(1, int(severity * self.severity_amplify_factor_for_entity))
        category = target_risk.category

        # Create entity generation chain
        chain_entity = PROMPT_ENTITY | self.llm | entity_parser
        chain_entity = chain_entity.with_retry(
            retry_if_exception_type=(OutputParserException,),
            wait_exponential_jitter=False,
            stop_after_attempt=self.NUM_RETRY["entity"],
        )

        # Generate entities
        entities_output: EntityFormat = chain_entity.invoke({"category": category, "n_entity": n_entity})
        entities = entities_output.entities

        # Generate summaries if web search is enabled
        if self.use_web_search:
            summaries = []
            for entity in entities:
                summary = web_search_and_summarize(self.llm, entity.strip())
                summaries.append(f"{entity.strip()}: {summary}")
        else:
            summaries = ["" for _ in entities]

        if len(entities) != len(summaries):
            raise ValueError("The number of entities and summaries must match.")

        self.logger.info(
            "Generated %d entities for %s",
            len(entities),
            target_risk.category,
            extra={"category": target_risk.category, "n_entities": len(entities)},
        )
        return entities, summaries

    def _generate_scenarios(self, target_risk: TargetRisk) -> list[str]:
        """Generate attack scenarios.

        Args:
            target_risk: Target risk to generate scenarios for

        Returns:
            List of generated scenarios

        """
        severity = target_risk.severity
        n_scenario = max(1, int(severity * self.severity_amplify_factor_for_scenario))
        category = target_risk.category

        # Create scenario generation chain
        chain_scenario = PROMPT_SCENARIO | self.llm | scenario_parser
        chain_scenario = chain_scenario.with_retry(
            retry_if_exception_type=(OutputParserException,),
            wait_exponential_jitter=False,
            stop_after_attempt=self.NUM_RETRY["scenario"],
        )

        # Generate scenarios
        scenarios_output: DetailAttackScenarioFormat = chain_scenario.invoke(
            {"category": category, "n_scenario": n_scenario}
        )

        scenarios = scenarios_output.scenarios
        self.logger.info(
            "Generated %d scenarios for %s",
            len(scenarios),
            target_risk.category,
            extra={"category": target_risk.category, "n_scenarios": len(scenarios)},
        )
        return scenarios

    def _generate_entity_prompts(
        self, target_risk: TargetRisk, entities: list[str], summaries: list[str]
    ) -> list[OutputPrompt]:
        """Generate prompts based on entities.

        Args:
            target_risk: Target risk
            entities: List of entities
            summaries: List of entity summaries

        Returns:
            List of generated prompts

        """
        category = target_risk.category
        description = target_risk.description
        prompts = []

        # Prepare batch input
        batched_input = []
        for entity, summary in tqdm(
            zip(entities, summaries),
            desc="Generating questions for each risk",
            total=len(entities),
            disable=not self.logger.isEnabledFor(logging.INFO),
        ):
            if self.length_pool:
                for length_limit in self.length_pool:
                    batched_input.append(
                        {
                            "category": category,
                            "entity": entity.strip(),
                            "summary": summary.strip(),
                            "min_length": length_limit.min_length,
                            "max_length": length_limit.max_length,
                            "description": description,
                        }
                    )
            else:
                batched_input.append(
                    {
                        "category": category,
                        "entity": entity.strip(),
                        "summary": summary.strip(),
                        "description": description,
                    }
                )

        # Generate prompts
        if self.length_pool:
            chain = PROMPT_GENERATE_RED_PROMPT_WITH_LENGTH | self.llm | generate_red_prompt_parser
        else:
            chain = PROMPT_GENERATE_RED_PROMPT | self.llm | generate_red_prompt_parser

        chain = chain.with_retry(
            retry_if_exception_type=(OutputParserException,),
            wait_exponential_jitter=False,
            stop_after_attempt=self.NUM_RETRY["question"],
        )

        question_outputs: list[GeneratedPromptFormat] = chain.batch(batched_input)

        # Process outputs
        if len(question_outputs) != len(batched_input):
            raise ValueError("The number of question outputs and batched inputs must match.")

        for question_output, item in zip(question_outputs, batched_input):
            question_text = question_output.question.strip()
            if not question_text:
                raise ValueError("Generated question output is empty.")

            # Prepare raw data
            if self.length_pool:
                raw_data = {
                    "entity": item["entity"],
                    "summary": item["summary"],
                    "raw_questions": question_text,
                    "length_limit": asdict(
                        LengthLimit(
                            min_length=cast(int, item["min_length"]),
                            max_length=cast(int, item["max_length"]),
                        )
                    ),
                }
            else:
                raw_data = {
                    "entity": item["entity"],
                    "summary": item["summary"],
                    "raw_questions": question_text,
                }

            prompts.append(
                OutputPrompt(
                    category=category,
                    prompt=question_text,
                    raw_data=raw_data,
                )
            )

        self.logger.info(
            "Generated %d entity-based prompts for %s",
            len(prompts),
            category,
            extra={"category": category, "n_prompts": len(prompts)},
        )
        return prompts

    def _generate_scenario_prompts(self, target_risk: TargetRisk, scenarios: list[str]) -> list[OutputPrompt]:
        """Generate prompts based on scenarios.

        Args:
            target_risk: Target risk
            scenarios: List of scenarios

        Returns:
            List of generated prompts

        """
        category = target_risk.category
        description = target_risk.description
        prompts = []

        # Prepare batch input
        batched_input = []
        for scenario in scenarios:
            if self.length_pool:
                for length_limit in self.length_pool:
                    batched_input.append(
                        {
                            "category": category,
                            "min_length": length_limit.min_length,
                            "max_length": length_limit.max_length,
                            "scenario": scenario.strip(),
                            "description": description,
                        }
                    )
            else:
                batched_input.append(
                    {
                        "category": category,
                        "entity": None,
                        "summary": None,
                        "scenario": scenario.strip(),
                        "description": description,
                    }
                )

        # Generate prompts
        if self.length_pool:
            chain = PROMPT_GENERATE_RED_PROMPT_SCENARIO_WITH_LENGTH | self.llm | generate_red_prompt_parser
        else:
            chain = PROMPT_GENERATE_RED_PROMPT_SCENARIO | self.llm | generate_red_prompt_parser

        chain = chain.with_retry(
            retry_if_exception_type=(OutputParserException,),
            wait_exponential_jitter=False,
            stop_after_attempt=self.NUM_RETRY["question"],
        )

        question_outputs: list[GeneratedPromptFormat] = chain.batch(batched_input)

        # Process outputs
        if len(question_outputs) != len(batched_input):
            raise ValueError("The number of question outputs and batched inputs must match.")

        for question_output, item in zip(question_outputs, batched_input):
            question_text = question_output.question.strip()
            if not question_text:
                raise ValueError("Generated question output is empty.")

            # Prepare raw data
            if self.length_pool:
                raw_data = {
                    "scenario": item["scenario"],
                    "raw_questions": question_text,
                    "length_limit": asdict(
                        LengthLimit(
                            min_length=cast(int, item["min_length"]),
                            max_length=cast(int, item["max_length"]),
                        )
                    ),
                }
            else:
                raw_data = {
                    "scenario": item["scenario"],
                    "raw_questions": question_text,
                }

            prompts.append(
                OutputPrompt(
                    category=category,
                    prompt=question_text,
                    raw_data=raw_data,
                )
            )

        self.logger.info(
            "Generated %d scenario-based prompts for %s",
            len(prompts),
            category,
            extra={"category": category, "n_prompts": len(prompts)},
        )
        return prompts

    def load_risk_data(self, risk_json: str) -> tuple[list[TargetRisk], Optional[list[LengthLimit]]]:
        """Load risk data from JSON file.

        Args:
            risk_json: Path to risk data JSON file
        Returns:
            Tuple of target risks and optional length limits

        """
        return load_risk(risk_json)

    def _estimate_prompt_count(self, target_risk: TargetRisk) -> int:
        """Estimate the number of prompts to be generated for a target risk.

        Args:
            target_risk: Target risk to estimate prompt count
        Returns:
            Estimated number of prompts

        """
        severity = target_risk.severity
        n_entity = max(1, int(severity * self.severity_amplify_factor_for_entity))
        n_scenario = max(1, int(severity * self.severity_amplify_factor_for_scenario))

        length_pool_size = len(self.length_pool) if self.length_pool else 1

        estimated_count = (n_entity + n_scenario) * length_pool_size
        return estimated_count
