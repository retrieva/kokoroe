"""Tests for ResponseGenerator class."""

import json
from unittest.mock import patch

import pytest

from auto_red_teaming_prompt.data import OutputPrompt, OutputResponse
from auto_red_teaming_prompt.generators.response import ResponseGenerator


@pytest.fixture
def mock_llm():
    """Create a fake LLM for testing."""
    from langchain_core.language_models import FakeListLLM

    # Provide enough responses for all tests
    responses = [f"Test response {i}" for i in range(1, 101)]
    return FakeListLLM(responses=responses)


@pytest.fixture
def sample_prompts():
    """Create sample prompts for testing."""
    return {
        "Test Category": [
            OutputPrompt(
                category="Test Category",
                prompt="Test prompt 1",
                raw_data={"test": "data1"},
            ),
            OutputPrompt(
                category="Test Category",
                prompt="Test prompt 2",
                raw_data={"test": "data2"},
            ),
        ]
    }


@pytest.fixture
def sample_prompt_file(tmp_path, sample_prompts):
    """Create a temporary prompt file."""
    prompt_data = {
        category: [
            {
                "category": item.category,
                "prompt": item.prompt,
                "raw_data": item.raw_data,
            }
            for item in items
        ]
        for category, items in sample_prompts.items()
    }

    prompt_file = tmp_path / "test_prompts.json"
    with open(prompt_file, "w", encoding="utf-8") as f:
        json.dump(prompt_data, f)
    return str(prompt_file)


class TestResponseGenerator:
    """Test cases for ResponseGenerator class."""

    def test_init(self, mock_llm, sample_prompt_file):
        """Test ResponseGenerator initialization."""
        generator = ResponseGenerator(
            llm=mock_llm,
        )

        assert generator.llm == mock_llm
        assert generator.chain is not None

    @patch("auto_red_teaming_prompt.generators.response.load_red_prompt")
    def test_generate(self, mock_load_red_prompt, mock_llm, sample_prompt_file, sample_prompts):
        """Test response generation."""
        mock_load_red_prompt.return_value = sample_prompts

        generator = ResponseGenerator(
            llm=mock_llm,
        )

        # FakeListLLM will automatically return responses in order
        data = generator.load_data(sample_prompt_file)
        result = generator.generate(data)

        assert "Test Category" in result
        assert len(result["Test Category"]) == 2

        # Check first response
        first_item = result["Test Category"][0]
        assert first_item["input"].prompt == "Test prompt 1"
        assert first_item["output"].response_text == "Test response 1"  # From FakeListLLM
        assert first_item["output"].response_status == "200"

        # Check second response
        second_item = result["Test Category"][1]
        assert second_item["input"].prompt == "Test prompt 2"
        assert second_item["output"].response_text == "Test response 2"  # From FakeListLLM
        assert second_item["output"].response_status == "200"

    def test_save_results(self, mock_llm, sample_prompt_file, tmp_path):
        """Test saving results to file."""
        generator = ResponseGenerator(
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
                }
            ]
        }

        output_file = tmp_path / "test_responses.json"
        generator.save_results(results, str(output_file))

        assert output_file.exists()

        with open(output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert "Test Category" in saved_data
        response_item = saved_data["Test Category"][0]
        assert response_item["input"]["prompt"] == "Test prompt"
        assert response_item["output"]["response_text"] == "Test response"
        assert response_item["output"]["response_status"] == "200"

    @patch("auto_red_teaming_prompt.generators.response.load_red_prompt")
    def test_empty_prompts(self, mock_load_red_prompt, mock_llm, sample_prompt_file):
        """Test handling of empty prompts."""
        mock_load_red_prompt.return_value = {}

        generator = ResponseGenerator(
            llm=mock_llm,
        )

        data = generator.load_data(sample_prompt_file)
        result = generator.generate(data)

        assert result == {}

    @patch("auto_red_teaming_prompt.generators.response.load_red_prompt")
    def test_multiple_categories(self, mock_load_red_prompt, mock_llm, sample_prompt_file):
        """Test handling multiple categories."""
        multi_category_prompts = {
            "Category A": [
                OutputPrompt(category="Category A", prompt="Prompt A", raw_data={}),
            ],
            "Category B": [
                OutputPrompt(category="Category B", prompt="Prompt B1", raw_data={}),
                OutputPrompt(category="Category B", prompt="Prompt B2", raw_data={}),
            ],
        }
        mock_load_red_prompt.return_value = multi_category_prompts

        generator = ResponseGenerator(
            llm=mock_llm,
        )

        # FakeListLLM will automatically handle multiple categories
        data = generator.load_data(sample_prompt_file)
        result = generator.generate(data)

        assert "Category A" in result
        assert "Category B" in result
        assert len(result["Category A"]) == 1
        assert len(result["Category B"]) == 2

        # FakeListLLM returns responses in order
        # First response for Category A, then two responses for Category B
        assert "Test response" in result["Category A"][0]["output"].response_text
        assert "Test response" in result["Category B"][0]["output"].response_text
        assert "Test response" in result["Category B"][1]["output"].response_text
