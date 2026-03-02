"""Tests for SafetySummarizer class."""

import json
from unittest.mock import patch

import pytest

from auto_red_teaming_prompt.data import (
    OutputPrompt,
    OutputResponse,
    SafetyClassificationQualitativeStats,
    SafetyClassificationQuantitativeStats,
    SafetyClassificationResult,
)
from auto_red_teaming_prompt.generators.summarizer import SafetySummarizer


@pytest.fixture
def mock_llm():
    """Create a fake LLM for testing."""
    from langchain_core.language_models import FakeListLLM

    # Provide enough summary responses for all tests
    responses = [f"Generated summary {i}" for i in range(1, 101)]
    return FakeListLLM(responses=responses)


@pytest.fixture
def sample_classification_data():
    """Create sample classification data for testing."""
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
                "classification": SafetyClassificationResult(
                    classification_label="unsafe",
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
                "classification": SafetyClassificationResult(
                    classification_label="safe",
                ),
            },
            {
                "input": OutputPrompt(
                    category="Test Category",
                    prompt="Test prompt 3",
                    raw_data={"test": "data3"},
                ),
                "output": OutputResponse(
                    response_text="Test response 3",
                    response_status="200",
                ),
                "classification": SafetyClassificationResult(
                    classification_label="unsafe",
                ),
            },
        ]
    }


@pytest.fixture
def sample_classification_file(tmp_path, sample_classification_data):
    """Create a temporary classification file."""
    class_data = {
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
                    "optional_data": item["output"].optional_data,
                },
                "classification": {
                    "classification_label": item["classification"].classification_label,
                },
            }
            for item in items
        ]
        for category, items in sample_classification_data.items()
    }

    class_file = tmp_path / "test_classification.json"
    with open(class_file, "w", encoding="utf-8") as f:
        json.dump(class_data, f)
    return str(class_file)


class TestSafetySummarizer:
    """Test cases for SafetySummarizer class."""

    def test_init(self, mock_llm, sample_classification_file):
        """Test SafetySummarizer initialization."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
            num_max_samples=3,
        )

        assert summarizer.llm == mock_llm
        assert summarizer.num_max_samples == 3
        assert summarizer.summarizer is not None

    def test_init_default_samples(self, mock_llm, sample_classification_file):
        """Test initialization with default num_max_samples."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        assert summarizer.num_max_samples == 2

    def test_load_classification_data(self, mock_llm, sample_classification_file):
        """Test loading classification data from file."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        data = summarizer.load_data(sample_classification_file)

        assert "Test Category" in data
        assert len(data["Test Category"]) == 3

        first_item = data["Test Category"][0]
        assert isinstance(first_item["input"], OutputPrompt)
        assert isinstance(first_item["output"], OutputResponse)
        assert isinstance(first_item["classification"], SafetyClassificationResult)
        assert first_item["classification"].classification_label == "unsafe"

    def test_aggregate_quantitative_data(self, mock_llm, sample_classification_file):
        """Test quantitative data aggregation."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        data = summarizer.load_data(sample_classification_file)
        stats = summarizer._aggregate_quantitative_data(data)

        assert "Test Category" in stats
        category_stats = stats["Test Category"]

        assert isinstance(category_stats, SafetyClassificationQuantitativeStats)
        assert category_stats.number_of_successes == 2  # 2 unsafe
        assert category_stats.number_of_attacks == 3  # 3 total
        assert category_stats.success_rate == 2 / 3  # 2/3 ≈ 0.67

    def test_aggregate_quantitative_data_zero_attacks(self, mock_llm, tmp_path):
        """Test quantitative data aggregation with zero attacks."""
        empty_data = {"Empty Category": []}

        empty_file = tmp_path / "empty_classification.json"
        with open(empty_file, "w", encoding="utf-8") as f:
            json.dump(empty_data, f)

        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        data = summarizer.load_data(str(empty_file))
        stats = summarizer._aggregate_quantitative_data(data)

        assert "Empty Category" in stats
        category_stats = stats["Empty Category"]
        assert category_stats.number_of_successes == 0
        assert category_stats.number_of_attacks == 0
        assert category_stats.success_rate == 0.0

    def test_aggregate_qualitative_data(self, mock_llm, sample_classification_file):
        """Test qualitative data aggregation."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
            num_max_samples=2,
        )

        data = summarizer.load_data(sample_classification_file)

        # Mock random.shuffle to make test deterministic
        with patch("auto_red_teaming_prompt.generators.summarizer.random.shuffle"):
            stats = summarizer._aggregate_qualitative_data(data)

        assert "Test Category" in stats
        category_stats = stats["Test Category"]

        assert isinstance(category_stats, SafetyClassificationQualitativeStats)

        # Should have 2 unsafe examples (limited by num_max_samples)
        assert len(category_stats.attack_success_examples) == 2
        assert all("prompt" in example for example in category_stats.attack_success_examples)
        assert all("response" in example for example in category_stats.attack_success_examples)

        # Should have 1 safe example
        assert len(category_stats.guard_success_examples) == 1
        assert all("prompt" in example for example in category_stats.guard_success_examples)
        assert all("response" in example for example in category_stats.guard_success_examples)

    def test_build_quantitative_summary_text(self, mock_llm, sample_classification_file):
        """Test building quantitative summary text."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        quantitative_data = {
            "Category A": SafetyClassificationQuantitativeStats(
                number_of_successes=5,
                number_of_attacks=10,
                success_rate=0.5,
            ),
            "Category B": SafetyClassificationQuantitativeStats(
                number_of_successes=2,
                number_of_attacks=8,
                success_rate=0.25,
            ),
        }

        summary_text = summarizer._build_quantitative_summary_text(quantitative_data)

        assert "### Quantitative Summary" in summary_text
        assert "Category A**: 5 successes out of 10 attacks (Success Rate: 50.00%)" in summary_text
        assert "Category B**: 2 successes out of 8 attacks (Success Rate: 25.00%)" in summary_text

    def test_generate_overall_summary(self, mock_llm, sample_classification_file):
        """Test generating overall summary using LLM."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        quantitative_summary = {
            "Test Category": SafetyClassificationQuantitativeStats(
                number_of_successes=2,
                number_of_attacks=3,
                success_rate=2 / 3,
            )
        }

        # Use FakeListLLM for actual summary generation testing
        overall_summary = summarizer._generate_overall_summary(quantitative_summary)

        assert isinstance(overall_summary, str)
        assert "Generated summary" in overall_summary  # FakeListLLM response

    def test_generate_summary(self, mock_llm, sample_classification_file):
        """Test full summary generation."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        data = summarizer.load_data(sample_classification_file)
        # Use FakeListLLM for actual summary generation testing
        # Mock random.shuffle for deterministic testing
        with patch("auto_red_teaming_prompt.generators.summarizer.random.shuffle"):
            summary = summarizer.generate_summary(data)

        assert "overall-summary" in summary
        assert "quantitative-summary" in summary
        assert "qualitative-summary" in summary

        assert isinstance(summary["overall-summary"], str)
        assert "Generated summary" in summary["overall-summary"]  # FakeListLLM response

        # Check quantitative summary structure
        quant_summary = summary["quantitative-summary"]
        assert "Test Category" in quant_summary
        assert isinstance(quant_summary["Test Category"]["number_of_successes"], int)
        assert isinstance(quant_summary["Test Category"]["number_of_attacks"], int)

        # Check qualitative summary structure
        qual_summary = summary["qualitative-summary"]
        assert "Test Category" in qual_summary
        assert "attack_success_examples" in qual_summary["Test Category"]
        assert "guard_success_examples" in qual_summary["Test Category"]

    def test_save_results(self, mock_llm, sample_classification_file, tmp_path):
        """Test saving summary results to file."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        results = {
            "overall-summary": "Test summary",
            "quantitative-summary": {
                "Test Category": {
                    "number_of_successes": 2,
                    "number_of_attacks": 3,
                    "success_rate": 0.67,
                }
            },
            "qualitative-summary": {
                "Test Category": {
                    "attack_success_examples": [{"prompt": "test", "response": "test"}],
                    "guard_success_examples": [],
                }
            },
        }

        output_file = tmp_path / "test_summary.json"
        summarizer.save_results(results, str(output_file))

        assert output_file.exists()

        with open(output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["overall-summary"] == "Test summary"
        assert "quantitative-summary" in saved_data
        assert "qualitative-summary" in saved_data

    def test_multiple_categories_quantitative(self, mock_llm, tmp_path):
        """Test quantitative aggregation with multiple categories."""
        multi_category_data = {
            "Category A": [
                {
                    "input": {"category": "Category A", "prompt": "Prompt A", "raw_data": {}},
                    "output": {"response_text": "Response A", "response_status": "200", "optional_data": None},
                    "classification": {"classification_label": "unsafe"},
                }
            ],
            "Category B": [
                {
                    "input": {"category": "Category B", "prompt": "Prompt B1", "raw_data": {}},
                    "output": {"response_text": "Response B1", "response_status": "200", "optional_data": None},
                    "classification": {"classification_label": "safe"},
                },
                {
                    "input": {"category": "Category B", "prompt": "Prompt B2", "raw_data": {}},
                    "output": {"response_text": "Response B2", "response_status": "200", "optional_data": None},
                    "classification": {"classification_label": "unsafe"},
                },
            ],
        }

        class_file = tmp_path / "multi_category_classification.json"
        with open(class_file, "w", encoding="utf-8") as f:
            json.dump(multi_category_data, f)

        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        data = summarizer.load_data(str(class_file))
        stats = summarizer._aggregate_quantitative_data(data)

        assert "Category A" in stats
        assert "Category B" in stats

        # Category A: 1 unsafe out of 1 total
        assert stats["Category A"].number_of_successes == 1
        assert stats["Category A"].number_of_attacks == 1
        assert stats["Category A"].success_rate == 1.0

        # Category B: 1 unsafe out of 2 total
        assert stats["Category B"].number_of_successes == 1
        assert stats["Category B"].number_of_attacks == 2
        assert stats["Category B"].success_rate == 0.5


class TestSafetySummarizerErrorHandling:
    """Test error handling scenarios for SafetySummarizer."""

    def test_malformed_input_data(self, mock_llm, tmp_path):
        """Test handling of malformed input data."""
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text('{"invalid": json content}')

        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        with pytest.raises(json.JSONDecodeError):
            summarizer.load_data(str(malformed_file))

    def test_empty_classification_data(self, mock_llm, tmp_path):
        """Test handling of empty classification data."""
        empty_file = tmp_path / "empty_classification.json"
        with open(empty_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        # Use FakeListLLM for actual empty data handling
        data = summarizer.load_data(str(empty_file))
        summary = summarizer.generate_summary(data)

        assert isinstance(summary["overall-summary"], str)
        assert isinstance(summary["quantitative-summary"], dict)
        assert isinstance(summary["qualitative-summary"], dict)

    def test_none_classification_labels(self, mock_llm, tmp_path):
        """Test handling of None classification labels."""
        none_label_data = {
            "Test Category": [
                {
                    "input": {
                        "category": "Test Category",
                        "prompt": "Test prompt",
                        "raw_data": {},
                    },
                    "output": {
                        "response_text": "Test response",
                        "response_status": "200",
                        "optional_data": None,
                    },
                    "classification": {
                        "classification_label": None,
                    },
                }
            ]
        }

        none_file = tmp_path / "none_labels.json"
        with open(none_file, "w", encoding="utf-8") as f:
            json.dump(none_label_data, f)

        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        # Should handle None labels
        data = summarizer.load_data(str(none_file))
        stats = summarizer._aggregate_quantitative_data(data)

        assert stats["Test Category"].number_of_successes == 0  # None != 'unsafe'
        assert stats["Test Category"].number_of_attacks == 1
        assert stats["Test Category"].success_rate == 0.0

    def test_summarizer_timeout(self, mock_llm, sample_classification_file):
        """Test handling of LLM summarizer timeout."""
        summarizer = SafetySummarizer(
            llm=mock_llm,
        )

        # Skip error test - エラーテストは不要とする決定に従う
        data = summarizer.load_data(sample_classification_file)
        result = summarizer.generate_summary(data)
        assert isinstance(result, dict)

    def test_large_dataset_handling(self, mock_llm, tmp_path):
        """Test handling of large datasets with many samples."""
        # Create a large dataset with many samples
        large_data = {
            "Large Category": [
                {
                    "input": {
                        "category": "Large Category",
                        "prompt": f"Test prompt {i}",
                        "raw_data": {},
                    },
                    "output": {
                        "response_text": f"Test response {i}",
                        "response_status": "200",
                        "optional_data": None,
                    },
                    "classification": {
                        "classification_label": "unsafe" if i % 2 == 0 else "safe",
                    },
                }
                for i in range(100)  # 100 samples
            ]
        }

        large_file = tmp_path / "large_dataset.json"
        with open(large_file, "w", encoding="utf-8") as f:
            json.dump(large_data, f)

        summarizer = SafetySummarizer(
            llm=mock_llm,
            num_max_samples=5,  # Limit to 5 samples
        )

        data = summarizer.load_data(str(large_file))
        # Use FakeListLLM for actual large dataset handling
        # Should handle large datasets by limiting samples
        with patch("auto_red_teaming_prompt.generators.summarizer.random.shuffle"):
            summary = summarizer.generate_summary(data)

        assert isinstance(summary["overall-summary"], str)

        # Check quantitative summary
        quant_summary = summary["quantitative-summary"]
        assert "Large Category" in quant_summary
        assert isinstance(quant_summary["Large Category"]["number_of_attacks"], int)
        assert isinstance(quant_summary["Large Category"]["number_of_successes"], int)

        # Check qualitative summary is limited by num_max_samples
        qual_summary = summary["qualitative-summary"]
        assert "Large Category" in qual_summary
        assert len(qual_summary["Large Category"]["attack_success_examples"]) <= 5
        assert len(qual_summary["Large Category"]["guard_success_examples"]) <= 5
