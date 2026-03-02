"""Tests for common utilities."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_red_teaming_prompt.utils.common import initialize_llm, load_json_data, save_json_data


class TestLoadJsonData:
    """Test load_json_data function."""

    def test_load_valid_json(self):
        """Test loading valid JSON data."""
        test_data = {"category1": [{"key": "value"}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = load_json_data(temp_path)
            assert result == test_data
        finally:
            Path(temp_path).unlink()

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_json_data("nonexistent.json")


class TestSaveJsonData:
    """Test save_json_data function."""

    def test_save_valid_data(self):
        """Test saving valid JSON data."""
        test_data = {"category1": [{"key": "value"}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_json_data(test_data, temp_path)

            # Verify data was saved correctly
            with open(temp_path, "r") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data
        finally:
            Path(temp_path).unlink()


class TestInitializeLlm:
    """Test initialize_llm function."""

    @patch("auto_red_teaming_prompt.utils.common.load_config_file")
    @patch("auto_red_teaming_prompt.utils.common.get_llm")
    def test_initialize_llm(self, mock_get_llm, mock_load_config):
        """Test LLM initialization."""
        mock_config = {"model": "test-model"}
        mock_load_config.return_value = mock_config
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        result = initialize_llm("test_type", "config.json")

        mock_load_config.assert_called_once_with("config.json", "test_type")
        mock_get_llm.assert_called_once_with(mock_config)
        assert result == mock_llm
