"""Tests for loading blue teaming data."""

import json
from dataclasses import asdict

import pytest

from auto_red_teaming_prompt.data import OutputPrompt, OutputResponse
from auto_red_teaming_prompt.tools import BlueTeamingDataLoader
from auto_red_teaming_prompt.utils import save_json_data


@pytest.fixture
def blue_teaming_input_file(tmp_path) -> str:
    """Fixture for blue teaming input file."""
    sample_data = {
        "Test Category": [
            {
                "input": asdict(
                    OutputPrompt(
                        category="Test Category",
                        prompt="Test prompt",
                    )
                ),
                "output": asdict(
                    OutputResponse(
                        response_text="Test negative output",
                        response_status="200",
                    )
                ),
                "improved_response": asdict(
                    OutputResponse(
                        response_text="Test improved output",
                        response_status="200",
                    )
                ),
            }
        ]
    }
    file_path = str(tmp_path / "blue_teaming_input.json")
    save_json_data(sample_data, file_path)
    return file_path


class TestBlueTeamingDataLoader:
    """Tests for loading blue teaming data."""

    def test_convert_to_sft_format(self, blue_teaming_input_file, tmp_path):
        """Test converting to SFT format."""
        data_loader = BlueTeamingDataLoader(blue_teaming_input_file)
        output_path = tmp_path / "sft_data.json"
        result_path = data_loader.convert_to_sft_format(str(output_path))
        assert result_path == str(output_path)
        assert output_path.is_file()

        expected_content = [
            {
                "messages": [
                    {"role": "user", "content": "Test prompt"},
                    {"role": "assistant", "content": "Test improved output"},
                ]
            }
        ]

        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == len(expected_content)
            for line, expected in zip(lines, expected_content):
                assert json.loads(line) == expected

    def test_convert_to_dpo_format(self, blue_teaming_input_file, tmp_path):
        """Test converting to DPO format."""
        data_loader = BlueTeamingDataLoader(blue_teaming_input_file)
        output_path = tmp_path / "dpo_data.json"
        result_path = data_loader.convert_to_dpo_format(str(output_path))
        assert result_path == str(output_path)
        assert output_path.is_file()

        expected_content = [
            {
                "input": {"messages": [{"role": "user", "content": "Test prompt"}]},
                "preferred_output": [{"role": "assistant", "content": "Test improved output"}],
                "non_preferred_output": [{"role": "assistant", "content": "Test negative output"}],
            }
        ]

        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == len(expected_content)
            for line, expected in zip(lines, expected_content):
                assert json.loads(line) == expected

    def test_compute_statistics(self, blue_teaming_input_file, tmp_path):
        """Test computing statistics."""
        data_loader = BlueTeamingDataLoader(blue_teaming_input_file)
        stats = data_loader.compute_statistics()
        assert stats is not None

        expected_stats = {
            "Test Category": {"num-examples": 1},
            "overall": {"num-examples": 1},
        }

        assert stats == expected_stats
