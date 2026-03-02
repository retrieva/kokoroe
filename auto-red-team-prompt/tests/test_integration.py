"""Integration tests for the full pipeline."""

import json
from unittest.mock import patch

import pytest

from auto_red_teaming_prompt.data import (
    LengthLimit,
    OutputPrompt,
    TargetRisk,
)
from auto_red_teaming_prompt.generators.evaluator import ResponseEvaluator
from auto_red_teaming_prompt.generators.red_prompt import RedPromptGenerator
from auto_red_teaming_prompt.generators.response import ResponseGenerator
from auto_red_teaming_prompt.generators.summarizer import SafetySummarizer


@pytest.fixture
def mock_llm():
    """Create a fake LLM for testing."""
    from langchain_core.language_models import FakeListLLM

    # Carefully ordered responses for each pipeline stage
    responses = [
        # For RedPromptGenerator entity generation (JSON format)
        '{"entities": ["Test Entity"]}',
        # For ResponseGenerator (text responses)
        "Test response 1",
        "Test response 2",
        "Test response 3",
        # For ResponseEvaluator (JSON classification format)
        "評価: [[safe]]",
        "評価: [[unsafe]]",
        # Additional responses
        '{"entities": ["Entity 1", "Entity 2"]}',
        "Test response 4",
        "Test response 5",
    ] * 20  # Repeat to provide enough responses
    return FakeListLLM(responses=responses)


@pytest.fixture
def sample_risk_file(tmp_path):
    """Create a sample risk file."""
    risk_data = {
        "target_risks": [
            {
                "category": "Test Category",
                "description": "Test description",
                "severity": 1,
            }
        ]
    }

    risk_file = tmp_path / "test_risks.json"
    with open(risk_file, "w", encoding="utf-8") as f:
        json.dump(risk_data, f)
    return str(risk_file)


class TestPipelineIntegration:
    """Test the full pipeline integration."""

    def test_full_pipeline_flow(self, mock_llm, sample_risk_file, tmp_path):
        """Test the complete pipeline from prompts to summary."""
        # Mock all the external dependencies
        with (
            patch("auto_red_teaming_prompt.generators.red_prompt.load_risk") as mock_load_risk,
            patch.object(RedPromptGenerator, "_generate_prompts_for_risk") as mock_generate_prompts,
            patch("auto_red_teaming_prompt.generators.response.load_red_prompt") as mock_load_red_prompt,
        ):
            # Setup risk data
            mock_risk = TargetRisk(category="Test Category", description="Test description", severity=1)
            mock_load_risk.return_value = ([mock_risk], None)

            # Setup generated prompts
            mock_prompt = OutputPrompt(
                category="Test Category",
                prompt="Test attack prompt",
                raw_data={"entity": "test entity"},
            )
            mock_generate_prompts.return_value = [mock_prompt]

            # Step 1: Generate red team prompts
            prompt_generator = RedPromptGenerator(
                llm=mock_llm,
                use_web_search=False,
            )

            risk_data = prompt_generator.load_risk_data(sample_risk_file)
            prompts = prompt_generator.generate(risk_data)
            prompts_file = tmp_path / "prompts.json"
            prompt_generator.save_results(prompts, str(prompts_file))

            # Verify prompts were generated
            assert "Test Category" in prompts
            assert len(prompts["Test Category"]) == 1
            assert prompts["Test Category"][0].prompt == "Test attack prompt"
            assert prompts_file.exists()

            # Step 2: Generate responses
            mock_load_red_prompt.return_value = prompts

            response_generator = ResponseGenerator(
                llm=mock_llm,
            )

            # FakeListLLM will automatically generate responses
            prompts_data = response_generator.load_data(str(prompts_file))
            responses = response_generator.generate(prompts_data)
            responses_file = tmp_path / "responses.json"
            response_generator.save_results(responses, str(responses_file))

            # Verify responses were generated
            assert "Test Category" in responses
            assert len(responses["Test Category"]) == 1
            response_item = responses["Test Category"][0]
            assert response_item["input"].prompt == "Test attack prompt"
            # FakeListLLM provides whatever response is next - just check it's not empty
            assert len(response_item["output"].response_text) > 0
            assert responses_file.exists()

            # Step 3: Evaluate responses
            evaluator = ResponseEvaluator(
                llm=mock_llm,
            )

            # FakeListLLM will automatically generate classifications
            responses_data = evaluator.load_data(str(responses_file))
            evaluations = evaluator.evaluate(responses_data)
            evaluations_file = tmp_path / "evaluations.json"
            evaluator.save_results(evaluations, str(evaluations_file))

            # Verify evaluations were generated
            assert "Test Category" in evaluations
            assert len(evaluations["Test Category"]) == 1
            eval_item = evaluations["Test Category"][0]
            assert eval_item["input"].prompt == "Test attack prompt"
            # FakeListLLM provides response, just check it exists
            assert len(eval_item["output"].response_text) > 0
            assert eval_item["classification"].classification_label in ["safe", "unsafe"]  # FakeListLLM classification
            assert evaluations_file.exists()

            # Step 4: Generate summary
            summarizer = SafetySummarizer(
                llm=mock_llm,
                num_max_samples=2,
            )

            # FakeListLLM will automatically generate summary
            # Mock random.shuffle for deterministic testing
            with patch("auto_red_teaming_prompt.generators.summarizer.random.shuffle"):
                evaluation_data = summarizer.load_data(str(evaluations_file))
                summary = summarizer.generate_summary(evaluation_data)

            summary_file = tmp_path / "summary.json"
            summarizer.save_results(summary, str(summary_file))

            # Verify summary was generated
            assert "overall-summary" in summary
            assert "quantitative-summary" in summary
            assert "qualitative-summary" in summary
            assert isinstance(summary["overall-summary"], str)  # FakeListLLM generated summary

            # Check quantitative summary
            quant_summary = summary["quantitative-summary"]
            assert "Test Category" in quant_summary
            assert quant_summary["Test Category"]["number_of_attacks"] == 1
            assert isinstance(quant_summary["Test Category"]["number_of_successes"], int)
            assert isinstance(quant_summary["Test Category"]["success_rate"], float)

            # Check qualitative summary
            qual_summary = summary["qualitative-summary"]
            assert "Test Category" in qual_summary
            assert isinstance(qual_summary["Test Category"]["guard_success_examples"], list)
            assert isinstance(qual_summary["Test Category"]["attack_success_examples"], list)

            assert summary_file.exists()

    def test_pipeline_with_multiple_categories(self, mock_llm, tmp_path):
        """Test pipeline with multiple risk categories."""
        # Create multi-category risk file
        risk_data = {
            "target_risks": [
                {
                    "category": "Category A",
                    "description": "Description A",
                    "severity": 1,
                },
                {
                    "category": "Category B",
                    "description": "Description B",
                    "severity": 1,
                },
            ]
        }

        risk_file = tmp_path / "multi_risks.json"
        with open(risk_file, "w", encoding="utf-8") as f:
            json.dump(risk_data, f)

        with (
            patch("auto_red_teaming_prompt.generators.red_prompt.load_risk") as mock_load_risk,
            patch.object(RedPromptGenerator, "_generate_prompts_for_risk") as mock_generate_prompts,
        ):
            # Setup risk data
            risks = [
                TargetRisk(category="Category A", description="Description A", severity=1),
                TargetRisk(category="Category B", description="Description B", severity=1),
            ]
            mock_load_risk.return_value = (risks, None)

            # Mock different prompts for each category
            def mock_prompts_side_effect(risk):
                return [
                    OutputPrompt(
                        category=risk.category,
                        prompt=f"Prompt for {risk.category}",
                        raw_data={"category": risk.category},
                    )
                ]

            mock_generate_prompts.side_effect = mock_prompts_side_effect

            # Generate prompts
            prompt_generator = RedPromptGenerator(
                llm=mock_llm,
                use_web_search=False,
            )

            risk_data = prompt_generator.load_risk_data(str(risk_file))
            prompts = prompt_generator.generate(risk_data)

            # Verify multi-category prompts
            assert "Category A" in prompts
            assert "Category B" in prompts
            assert len(prompts["Category A"]) == 1
            assert len(prompts["Category B"]) == 1
            assert prompts["Category A"][0].prompt == "Prompt for Category A"
            assert prompts["Category B"][0].prompt == "Prompt for Category B"

    def test_pipeline_error_handling(self, mock_llm, sample_risk_file):
        """Test pipeline error handling."""
        with patch("auto_red_teaming_prompt.generators.red_prompt.load_risk") as mock_load_risk:
            # Simulate error in risk loading
            mock_load_risk.side_effect = FileNotFoundError("Risk file not found")

            prompt_generator = RedPromptGenerator(
                llm=mock_llm,
                use_web_search=False,
            )

            # Should raise the error
            with pytest.raises(FileNotFoundError, match="Risk file not found"):
                data = prompt_generator.load_risk_data("nonexistent_file.json")
                prompt_generator.generate(data)

    def test_pipeline_with_length_limits(self, mock_llm, sample_risk_file, tmp_path):
        """Test pipeline with length limit constraints."""
        length_limits = [
            LengthLimit(min_length=50, max_length=100),
            LengthLimit(min_length=100, max_length=200),
        ]

        with (
            patch("auto_red_teaming_prompt.generators.red_prompt.load_risk") as mock_load_risk,
            patch.object(RedPromptGenerator, "_generate_prompts_for_risk") as mock_generate_prompts,
        ):
            # Setup risk data with length limits
            mock_risk = TargetRisk(category="Test Category", description="Test description", severity=1)
            mock_load_risk.return_value = ([mock_risk], length_limits)

            # Mock prompts with length limit data
            mock_prompts = [
                OutputPrompt(
                    category="Test Category",
                    prompt="Short prompt",
                    raw_data={
                        "entity": "test",
                        "length_limit": {"min_length": 50, "max_length": 100},
                    },
                ),
                OutputPrompt(
                    category="Test Category",
                    prompt="Longer prompt for testing",
                    raw_data={
                        "entity": "test",
                        "length_limit": {"min_length": 100, "max_length": 200},
                    },
                ),
            ]
            mock_generate_prompts.return_value = mock_prompts

            # Generate prompts with length limits
            prompt_generator = RedPromptGenerator(
                llm=mock_llm,
                use_web_search=False,
            )

            risk_data = prompt_generator.load_risk_data(sample_risk_file)
            prompts = prompt_generator.generate(risk_data)

            # Verify length limits were applied
            assert "Test Category" in prompts
            assert len(prompts["Test Category"]) == 2

            # Check that length limit information is preserved
            for prompt in prompts["Test Category"]:
                assert "length_limit" in prompt.raw_data  # type: ignore
                length_limit = prompt.raw_data["length_limit"]  # type: ignore
                assert "min_length" in length_limit
                assert "max_length" in length_limit

    def test_file_format_consistency(self, mock_llm, sample_risk_file, tmp_path):
        """Test that file formats are consistent across pipeline stages."""
        with (
            patch("auto_red_teaming_prompt.generators.red_prompt.load_risk") as mock_load_risk,
            patch.object(RedPromptGenerator, "_generate_prompts_for_risk") as mock_generate_prompts,
        ):
            # Setup minimal test data
            mock_risk = TargetRisk(category="Test", description="Test", severity=1)
            mock_load_risk.return_value = ([mock_risk], None)

            mock_prompt = OutputPrompt(
                category="Test",
                prompt="Test prompt",
                raw_data={"test": "data"},
            )
            mock_generate_prompts.return_value = [mock_prompt]

            # Generate and save prompts
            prompt_generator = RedPromptGenerator(
                llm=mock_llm,
                use_web_search=False,
            )

            risk_data = prompt_generator.load_risk_data(sample_risk_file)
            prompts = prompt_generator.generate(risk_data)
            prompts_file = tmp_path / "test_prompts.json"
            prompt_generator.save_results(prompts, str(prompts_file))

            # Verify prompts file format
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts_data = json.load(f)

            assert "Test" in prompts_data
            prompt_item = prompts_data["Test"][0]
            required_keys = {"category", "prompt", "raw_data"}
            assert set(prompt_item.keys()) == required_keys

            # Test that response generator can load this format
            response_generator = ResponseGenerator(
                llm=mock_llm,
            )

            # Use FakeListLLM for actual pipeline testing
            prompt_data = response_generator.load_data(str(prompts_file))
            responses = response_generator.generate(prompt_data)

            # Verify responses format
            assert "Test" in responses
            response_item = responses["Test"][0]
            assert "input" in response_item
            assert "output" in response_item
            assert isinstance(response_item["input"], OutputPrompt)

            # Save and test evaluator compatibility
            responses_file = tmp_path / "test_responses.json"
            response_generator.save_results(responses, str(responses_file))

            evaluator = ResponseEvaluator(
                llm=mock_llm,
            )

            # Use FakeListLLM for actual classification pipeline testing
            response_data = evaluator.load_data(str(responses_file))
            evaluations = evaluator.evaluate(response_data)
            assert "Test" in evaluations
