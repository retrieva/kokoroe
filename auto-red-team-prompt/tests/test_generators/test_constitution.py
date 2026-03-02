"""Tests for ConstitutionGenerator class."""

import json
from dataclasses import asdict

import pytest

from auto_red_teaming_prompt.data import ConstitutionData, SafetyClassificationQuantitativeStats, TargetRisk
from auto_red_teaming_prompt.generators.constitution import ConstitutionGenerator


@pytest.fixture
def mock_llm():
    """Create a fake LLM for testing."""
    from langchain_core.language_models import FakeListLLM

    responses = [
        '["New Constitution 1", "New Constitution 2", "New Constitution 3"]',
    ]
    return FakeListLLM(responses=responses)


@pytest.fixture
def sample_input_data():
    """Create sample input data for testing."""
    sample = {
        "attack-scenario": [
            TargetRisk(
                category="Test Category 1",
                description="Description of Test Category 1",
                severity=1,
                examples=None,
            ),
            TargetRisk(
                category="Test Category 2",
                description="Description of Test Category 2",
                severity=2,
                examples=None,
            ),
        ],
        "quantitative-summary": {
            "Test Category 1": SafetyClassificationQuantitativeStats(
                number_of_attacks=50,
                number_of_successes=25,
                success_rate=0.5,
            ),
            "Test Category 2": SafetyClassificationQuantitativeStats(
                number_of_attacks=30,
                number_of_successes=3,
                success_rate=0.1,
            ),
        },
        "llm-constitution": ConstitutionData(texts=["Existing Constitution 1", "Existing Constitution 2"]),
    }
    return sample


@pytest.fixture
def sample_input_file(tmp_path, sample_input_data):
    """Create a temporary input file."""
    input_path = tmp_path / "sample_input.json"
    with open(input_path, "w") as f:
        json.dump(
            {
                "attack-scenario": [asdict(item) for item in sample_input_data["attack-scenario"]],
                "quantitative-summary": {
                    category: asdict(stats) for category, stats in sample_input_data["quantitative-summary"].items()
                },
                "llm-constitutions": sample_input_data["llm-constitution"].texts,
            },
            f,
            indent=2,
        )
    return str(input_path)


class TestConstitutionGenerator:
    """Test cases for ConstitutionGenerator class."""

    def test_init(self, mock_llm):
        """Test ConstitutionGenerator initialization"""
        generator = ConstitutionGenerator(mock_llm)
        assert generator.llm == mock_llm
        assert generator.chain is not None

    def test_load_input_data(self, mock_llm, sample_input_file):
        """Test loading input data from a file."""
        generator = ConstitutionGenerator(mock_llm)
        data = generator.load_data(sample_input_file)

        constitution = data["current_constitution"]
        red_teaming_results = data["red_teaming_results"]
        attack_scenario = data["attack_scenario"]

        assert isinstance(constitution, ConstitutionData)
        assert len(constitution.texts) == 2
        assert constitution.texts[0] == "Existing Constitution 1"

        assert isinstance(red_teaming_results, dict)
        assert "Test Category 1" in red_teaming_results
        stats1 = red_teaming_results["Test Category 1"]
        assert isinstance(stats1, SafetyClassificationQuantitativeStats)
        assert stats1.number_of_attacks == 50
        assert stats1.number_of_successes == 25
        assert stats1.success_rate == 0.5

        assert isinstance(attack_scenario, list)
        assert len(attack_scenario) == 2
        assert attack_scenario[0].category == "Test Category 1"

    def test_generate(self, mock_llm, sample_input_file):
        """Test generating new constitutions."""
        generator = ConstitutionGenerator(mock_llm)
        data = generator.load_data(sample_input_file)
        output = generator.generate(data)

        assert isinstance(output, ConstitutionData)
        assert len(output.texts) == 3
        assert output.texts[0] == "New Constitution 1"

    def test_save_results(self, mock_llm, tmp_path):
        """Test saving results to a file."""
        generator = ConstitutionGenerator(mock_llm)
        results = ConstitutionData(texts=["Saved Constitution 1", "Saved Constitution 2"])
        output_file = tmp_path / "output.json"
        generator.save_results(results, str(output_file))

        assert output_file.exists()

        with open(output_file, "r") as f:
            data = json.load(f)
        assert "texts" in data
        assert len(data["texts"]) == 2
        assert data["texts"][0] == "Saved Constitution 1"

    def test_empty_evaluation_data(self, mock_llm, tmp_path):
        """Test handling of empty evaluation data."""
        generator = ConstitutionGenerator(mock_llm)
        results = ConstitutionData(texts=[])
        output_file = tmp_path / "output.json"
        generator.save_results(results, str(output_file))

        assert output_file.exists()

        with open(output_file, "r") as f:
            data = json.load(f)

        assert "texts" in data
        assert len(data["texts"]) == 0
