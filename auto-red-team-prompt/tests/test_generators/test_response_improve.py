"""Tests for response improvement generator."""

import json
from dataclasses import asdict

import pytest

from auto_red_teaming_prompt.data import ConstitutionData, OutputPrompt, OutputResponse, ResponseImproverInput
from auto_red_teaming_prompt.generators import ResponseImprover


@pytest.fixture
def mock_llm():
    """Create a fake LLM for testing."""
    from langchain_core.language_models import FakeListLLM

    responses = ['{"improved_response": "改善された回答1"}'] * 50  # 50 responses
    return FakeListLLM(responses=responses)


@pytest.fixture
def sample_response_data() -> dict[str, list[dict[str, OutputPrompt | OutputResponse]]]:
    """Create sample response data for testing."""
    response = {
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
        ]
    }
    return response


@pytest.fixture
def sample_constitution_data() -> ConstitutionData:
    """Create sample constitution data for testing."""
    return ConstitutionData(texts=["Constitution text 1", "Constitution text 2"])


@pytest.fixture
def sample_response_file(tmp_path, sample_response_data):
    """Create a temporary response file."""
    evaluation_data = {
        category: [{k: asdict(v) for k, v in item.items()} for item in items]
        for category, items in sample_response_data.items()
    }

    response_file = tmp_path / "responses.json"
    with open(response_file, "w", encoding="utf-8") as f:
        json.dump(evaluation_data, f, ensure_ascii=False, indent=4)
    return str(response_file)


@pytest.fixture
def sample_constitution_file(tmp_path, sample_constitution_data):
    """Create a temporary constitution file."""
    constitution_file = tmp_path / "constitution.json"
    with open(constitution_file, "w", encoding="utf-8") as f:
        json.dump({"texts": sample_constitution_data.texts}, f, ensure_ascii=False, indent=4)
    return str(constitution_file)


class TestResponseImprover:
    """Test cases for ResponseImprover class."""

    def test_init(self, mock_llm):
        """Test initialization of ResponseImprover."""
        improver = ResponseImprover(llm=mock_llm)
        assert improver.llm == mock_llm
        assert hasattr(improver, "chain")

    def test_load_data(self, mock_llm, sample_response_file, sample_constitution_file):
        """Test loading of input data."""
        improver = ResponseImprover(llm=mock_llm)
        input_data = improver.load_data(
            response_file=sample_response_file,
            constitution_file=sample_constitution_file,
        )
        assert isinstance(input_data, ResponseImproverInput)

        response_data = input_data.responses
        assert "Test Category" in response_data
        assert len(response_data["Test Category"]) == 1

        constitution_data = input_data.constitution
        assert isinstance(constitution_data, ConstitutionData)
        assert len(constitution_data.texts) == 2

    def test_generate(self, mock_llm, sample_response_file, sample_constitution_file):
        """Test the generate method of ResponseImprover."""
        improver = ResponseImprover(llm=mock_llm)
        input_data = improver.load_data(
            response_file=sample_response_file,
            constitution_file=sample_constitution_file,
        )
        output = improver.generate(input_data)
        assert isinstance(output, dict)
        assert "Test Category" in output
        assert len(output["Test Category"]) == 1
        for item in output["Test Category"]:
            assert "input" in item
            assert "output" in item
            assert isinstance(item["input"], OutputPrompt)
            assert isinstance(item["output"], OutputResponse)

    def test_save_data(self, mock_llm, sample_response_file, sample_constitution_file, tmp_path):
        """Test saving of improved responses."""
        improver = ResponseImprover(llm=mock_llm)
        input_data = improver.load_data(
            response_file=sample_response_file,
            constitution_file=sample_constitution_file,
        )
        output = improver.generate(input_data)

        output_file = tmp_path / "improved_responses.json"
        improver.save_results(output, output_file)

        # Load the saved data and verify its content
        with open(output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        formatted_output = {
            category: [{k: asdict(v) for k, v in item.items()} for item in items] for category, items in output.items()
        }

        assert saved_data == formatted_output

    def test_empty_input(self, mock_llm):
        """Test handling of empty input data."""
        improver = ResponseImprover(llm=mock_llm)
        empty_input = ResponseImproverInput(responses={}, constitution=ConstitutionData(texts=[]))
        output = improver.generate(empty_input)
        assert output == {}
