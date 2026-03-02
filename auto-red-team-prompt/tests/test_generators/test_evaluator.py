"""Tests for ResponseEvaluator class."""

import json

import pytest

from auto_red_teaming_prompt.data import (
    OutputPrompt,
    OutputResponse,
    SafetyClassificationResult,
)
from auto_red_teaming_prompt.generators.evaluator import ResponseEvaluator


@pytest.fixture
def mock_llm():
    """Create a fake LLM for testing."""
    from langchain_core.language_models import FakeListLLM

    # Provide JSON-formatted responses for classification chain
    responses = ["評価: [[safe]]", "評価: [[unsafe]]"] * 50  # 100 responses
    return FakeListLLM(responses=responses)


@pytest.fixture
def sample_evaluation_data():
    """Create sample evaluation data for testing."""
    return {
        "Test Category": [
            {
                "input": OutputPrompt(
                    category="Test Category",
                    prompt="Test prompt 1",
                    raw_data={"test": "data1"},
                ),
                "output": OutputResponse(
                    response_text="Test response 1",
                    response_status="200",
                ),
            },
            {
                "input": OutputPrompt(
                    category="Test Category",
                    prompt="Test prompt 2",
                    raw_data={"test": "data2"},
                ),
                "output": OutputResponse(
                    response_text="Test response 2",
                    response_status="200",
                ),
            },
        ]
    }


@pytest.fixture
def sample_evaluation_file(tmp_path, sample_evaluation_data):
    """Create a temporary evaluation file."""
    eval_data = {
        category: [
            {
                "input": {
                    "category": item["input"].category,
                    "prompt": item["input"].prompt,
                    "raw_data": item["input"].raw_data,
                },
                "output": {
                    "response_text": item["output"].response_text,
                    "response_status": item["output"].response_status,
                },
            }
            for item in items
        ]
        for category, items in sample_evaluation_data.items()
    }

    eval_file = tmp_path / "test_evaluation.json"
    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(eval_data, f)
    return str(eval_file)


class TestResponseEvaluator:
    """Test cases for ResponseEvaluator class."""

    def test_init(self, mock_llm, sample_evaluation_file):
        """Test ResponseEvaluator initialization."""
        evaluator = ResponseEvaluator(
            llm=mock_llm,
        )

        assert evaluator.llm == mock_llm
        assert evaluator.classification_chain is not None

    def test_load_evaluation_data(self, mock_llm, sample_evaluation_file):
        """Test loading evaluation data from file."""
        evaluator = ResponseEvaluator(
            llm=mock_llm,
        )

        data = evaluator.load_data(sample_evaluation_file)

        assert "Test Category" in data
        assert len(data["Test Category"]) == 2

        first_item = data["Test Category"][0]
        assert isinstance(first_item["input"], OutputPrompt)
        assert isinstance(first_item["output"], OutputResponse)
        assert first_item["input"].prompt == "Test prompt 1"
        assert first_item["output"].response_text == "Test response 1"

    def test_evaluate(self, mock_llm, sample_evaluation_file):
        """Test response evaluation."""
        evaluator = ResponseEvaluator(
            llm=mock_llm,
        )

        # Use FakeListLLM for actual evaluation pipeline testing
        data = evaluator.load_data(sample_evaluation_file)
        result = evaluator.evaluate(data)

        assert "Test Category" in result
        assert len(result["Test Category"]) == 2

        # Check first evaluation result
        first_result = result["Test Category"][0]
        assert first_result["input"].prompt == "Test prompt 1"
        assert first_result["output"].response_text == "Test response 1"
        assert first_result["classification"].classification_label in ["safe", "unsafe"]  # FakeListLLM JSON result

        # Check second evaluation result
        second_result = result["Test Category"][1]
        assert second_result["input"].prompt == "Test prompt 2"
        assert second_result["output"].response_text == "Test response 2"
        assert second_result["classification"].classification_label in ["safe", "unsafe"]  # FakeListLLM JSON result

    def test_evaluate_normal_case(self, mock_llm, sample_evaluation_file):
        """Test normal evaluation case with FakeListLLM."""
        evaluator = ResponseEvaluator(
            llm=mock_llm,
        )

        # Test normal evaluation with FakeListLLM
        data = evaluator.load_data(sample_evaluation_file)
        result = evaluator.evaluate(data)

        # Verify basic structure
        assert isinstance(result, dict)
        assert "Test Category" in result
        assert len(result["Test Category"]) == 2

        # Verify each item has required fields
        for item in result["Test Category"]:
            assert "input" in item
            assert "output" in item
            assert "classification" in item

    def test_save_results(self, mock_llm, sample_evaluation_file, tmp_path):
        """Test saving evaluation results to file."""
        evaluator = ResponseEvaluator(
            llm=mock_llm,
        )

        results = {
            "Test Category": [
                {
                    "input": OutputPrompt(
                        category="Test Category",
                        prompt="Test prompt",
                        raw_data={"test": "data"},
                    ),
                    "output": OutputResponse(
                        response_text="Test response",
                        response_status="200",
                    ),
                    "classification": SafetyClassificationResult(
                        classification_label="safe",
                    ),
                }
            ]
        }

        output_file = tmp_path / "test_evaluations.json"
        evaluator.save_results(results, str(output_file))

        assert output_file.exists()

        with open(output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert "Test Category" in saved_data
        eval_item = saved_data["Test Category"][0]
        assert eval_item["input"]["prompt"] == "Test prompt"
        assert eval_item["output"]["response_text"] == "Test response"
        assert eval_item["classification"]["classification_label"] == "safe"

    def test_empty_evaluation_data(self, mock_llm, tmp_path):
        """Test handling of empty evaluation data."""
        empty_eval_file = tmp_path / "empty_evaluation.json"
        with open(empty_eval_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        evaluator = ResponseEvaluator(
            llm=mock_llm,
        )

        data = evaluator.load_data(str(empty_eval_file))
        result = evaluator.evaluate(data)

        assert result == {}

    def test_multiple_categories(self, mock_llm, tmp_path):
        """Test handling multiple categories."""
        multi_category_data = {
            "Category A": [
                {
                    "input": {
                        "category": "Category A",
                        "prompt": "Prompt A",
                        "raw_data": {},
                    },
                    "output": {
                        "response_text": "Response A",
                        "response_status": "200",
                    },
                }
            ],
            "Category B": [
                {
                    "input": {
                        "category": "Category B",
                        "prompt": "Prompt B",
                        "raw_data": {},
                    },
                    "output": {
                        "response_text": "Response B",
                        "response_status": "200",
                    },
                }
            ],
        }

        eval_file = tmp_path / "multi_category_evaluation.json"
        with open(eval_file, "w", encoding="utf-8") as f:
            json.dump(multi_category_data, f)

        evaluator = ResponseEvaluator(
            llm=mock_llm,
        )

        # Use FakeListLLM for actual multi-category evaluation
        data = evaluator.load_data(str(eval_file))
        result = evaluator.evaluate(data)

        assert "Category A" in result
        assert "Category B" in result
        assert len(result["Category A"]) == 1
        assert len(result["Category B"]) == 1
        assert result["Category A"][0]["classification"].classification_label in ["safe", "unsafe"]
        assert result["Category B"][0]["classification"].classification_label in ["safe", "unsafe"]
