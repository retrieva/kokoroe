"""Tests for extracting results for red prompts."""

from auto_red_teaming_prompt.data import (
    RedTeamingResultForBlueTeaming,
    SafetyClassificationQuantitativeStats,
    TargetRisk,
)
from auto_red_teaming_prompt.tools import update_with_vulnerability_summary


class TestRedPromptExtract:
    """Tests for extracting results for red prompts."""

    def test_update_with_vulnerability_summary(self):
        """Test updating with vulnerability summary."""
        original_severity = 5
        attack_success_rate = 0.3

        input_risk = [
            TargetRisk(
                category="Test Category",
                description="Test Description",
                severity=original_severity,
                examples=["Example 1", "Example 2"],
            )
        ]
        input_summary = {
            "Test Category": RedTeamingResultForBlueTeaming(
                vulnerability_stats=SafetyClassificationQuantitativeStats(
                    number_of_successes=3,
                    number_of_attacks=10,
                    success_rate=attack_success_rate,
                ),
                severity=original_severity,
            )
        }

        expected_output = [
            TargetRisk(
                category="Test Category",
                description="Test Description",
                severity=original_severity * attack_success_rate,
                examples=["Example 1", "Example 2"],
            )
        ]

        output = update_with_vulnerability_summary(input_risk, input_summary)
        assert output == expected_output
