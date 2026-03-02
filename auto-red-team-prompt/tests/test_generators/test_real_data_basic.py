"""Basic tests with real data files for Issue #19."""

import json
from pathlib import Path

from auto_red_teaming_prompt.data import LengthLimit, TargetRisk, load_risk


class TestRealDataLoading:
    """Test loading real data files specified in Issue #19."""

    def test_load_sample_json(self):
        """Test loading sample.json correctly."""
        sample_path = "target-risks/sample.json"
        assert Path(sample_path).exists(), f"Sample file {sample_path} does not exist"

        # Test with load_risk function
        target_risks, length_pool = load_risk(sample_path)

        # Verify structure
        assert len(target_risks) == 2
        assert length_pool is None  # sample.json doesn't have length-pool

        # Verify risk data structure
        for risk in target_risks:
            assert isinstance(risk, TargetRisk)
            assert hasattr(risk, "category")
            assert hasattr(risk, "description")
            assert hasattr(risk, "severity")
            assert hasattr(risk, "examples")

        # Check specific categories
        categories = [risk.category for risk in target_risks]
        assert "Hate/Hate-Speech/Race" in categories
        assert "Deception/Fraud/Spam" in categories

    def test_load_sample_input_json(self):
        """Test loading sample-input.json with length-pool."""
        sample_input_path = "target-risks/sample-input.json"
        assert Path(sample_input_path).exists(), f"Sample input file {sample_input_path} does not exist"

        # Test with load_risk function
        target_risks, length_pool = load_risk(sample_input_path)

        # Verify structure
        assert len(target_risks) == 2
        assert length_pool is not None  # sample-input.json has length-pool
        assert len(length_pool) == 2

        # Verify length pool
        for limit in length_pool:
            assert isinstance(limit, LengthLimit)
            assert hasattr(limit, "min_length")
            assert hasattr(limit, "max_length")

        # Check specific length constraints
        assert length_pool[0].min_length == 0
        assert length_pool[0].max_length == 20
        assert length_pool[1].min_length == 40
        assert length_pool[1].max_length == 100

        # Verify risk data is same as sample.json
        categories = [risk.category for risk in target_risks]
        assert "Hate/Hate-Speech/Race" in categories
        assert "Deception/Fraud/Spam" in categories

    def test_data_format_consistency(self):
        """Test that both files have consistent data format."""
        sample_path = "target-risks/sample.json"
        sample_input_path = "target-risks/sample-input.json"

        risks1, _ = load_risk(sample_path)
        risks2, _ = load_risk(sample_input_path)

        # Should have same number of risks
        assert len(risks1) == len(risks2)

        # Should have same categories (order might differ)
        categories1 = set(risk.category for risk in risks1)
        categories2 = set(risk.category for risk in risks2)
        assert categories1 == categories2

    def test_risk_data_completeness(self):
        """Test that risk data has all required fields."""
        sample_path = "target-risks/sample.json"
        risks, _ = load_risk(sample_path)

        for risk in risks:
            # Required fields
            assert isinstance(risk.category, str)
            assert len(risk.category) > 0

            assert isinstance(risk.description, str)
            assert len(risk.description) > 0

            assert isinstance(risk.severity, int)
            assert 1 <= risk.severity <= 5

            # Examples can be empty list
            assert isinstance(risk.examples, list)


class TestRealDataStructure:
    """Test the structure of real data files."""

    def test_json_structure_sample(self):
        """Test JSON structure of sample.json."""
        with open("target-risks/sample.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # Must have attack-scenario key
        assert "attack-scenario" in data
        assert isinstance(data["attack-scenario"], list)
        assert len(data["attack-scenario"]) > 0

        # Check each scenario structure
        for scenario in data["attack-scenario"]:
            assert "category" in scenario
            assert "description" in scenario
            assert "severity" in scenario
            assert "examples" in scenario

    def test_json_structure_sample_input(self):
        """Test JSON structure of sample-input.json."""
        with open("target-risks/sample-input.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # Must have attack-scenario key
        assert "attack-scenario" in data
        assert isinstance(data["attack-scenario"], list)

        # Must have other-conditions with length-pool
        assert "other-conditions" in data
        assert "length-pool" in data["other-conditions"]
        assert isinstance(data["other-conditions"]["length-pool"], list)
        assert len(data["other-conditions"]["length-pool"]) > 0

        # Check length-pool structure
        for pool in data["other-conditions"]["length-pool"]:
            assert "min" in pool
            assert "max" in pool
            assert isinstance(pool["min"], int)
            assert isinstance(pool["max"], int)
            assert pool["min"] <= pool["max"]

    def test_severity_values(self):
        """Test that severity values are in the expected 1-5 range."""
        sample_path = "target-risks/sample.json"
        risks, _ = load_risk(sample_path)

        for risk in risks:
            # Current spec: 1-5
            assert 1 <= risk.severity <= 5, f"Severity {risk.severity} out of expected range for {risk.category}"

    def test_examples_structure(self):
        """Test examples field structure in sample-input.json."""
        sample_input_path = "target-risks/sample-input.json"

        with open(sample_input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check that examples are provided in sample-input.json
        hate_speech_scenario = None
        for scenario in data["attack-scenario"]:
            if "Hate" in scenario["category"]:
                hate_speech_scenario = scenario
                break

        assert hate_speech_scenario is not None
        assert isinstance(hate_speech_scenario["examples"], list)
        # sample-input.json should have example texts
        assert len(hate_speech_scenario["examples"]) > 0
