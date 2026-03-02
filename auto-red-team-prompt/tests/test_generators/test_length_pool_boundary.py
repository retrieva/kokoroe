"""Tests for length-pool boundary behavior (closed intervals)."""

import json
from pathlib import Path


def _make_fake_llm_for_boundary(severity: int, n_ranges: int):
    """Return a FakeListLLM that yields JSON for all stages.

    Order:
      1) entities JSON
      2) scenarios JSON
      3) questions JSON for entity-based prompts (n_entity * n_ranges)
      4) questions JSON for scenario-based prompts (n_scenario * n_ranges)
    """
    from langchain_core.language_models import FakeListLLM

    SEVERITY_AMPLIFY_FACTOR_FOR_ENTITY = 5
    SEVERITY_AMPLIFY_FACTOR_FOR_SCENARIO = 2

    n_entity = max(1, int(severity * SEVERITY_AMPLIFY_FACTOR_FOR_ENTITY))
    n_scenario = max(1, int(severity * SEVERITY_AMPLIFY_FACTOR_FOR_SCENARIO))

    entities_json = json.dumps({"entities": [f"E{i + 1}" for i in range(n_entity)]})
    scenarios_json = json.dumps({"scenarios": [f"S{i + 1}" for i in range(n_scenario)]})

    n_questions = n_entity * n_ranges + n_scenario * n_ranges
    question_jsons = [json.dumps({"question": "Q"})] * n_questions

    return FakeListLLM(responses=[entities_json, scenarios_json, *question_jsons])


def test_length_pool_boundaries_closed_interval(tmp_path: Path):
    """Length limits are passed through as provided (closed interval)."""
    # Prepare minimal risk data with length-pool
    risk_data = {
        "attack-scenario": [
            {
                "category": "Test/Boundary",
                "description": "Boundary test",
                "examples": [],
                "severity": 1,
            }
        ],
        "other-conditions": {
            "length-pool": [
                {"min": 10, "max": 10},  # exact length
                {"min": 0, "max": 20},  # range
            ]
        },
    }

    risk_file = tmp_path / "risks.json"
    with risk_file.open("w", encoding="utf-8") as f:
        json.dump(risk_data, f)

    # Fake LLM with proper response sequence for severity=1 and 2 ranges
    llm = _make_fake_llm_for_boundary(severity=1, n_ranges=2)

    from auto_red_teaming_prompt.generators.red_prompt import RedPromptGenerator

    generator = RedPromptGenerator(llm=llm)
    data = generator.load_risk_data(str(risk_file))
    results = generator.generate(data)

    # Validate that length limits are preserved in raw_data
    bounds = {(10, 10), (0, 20)}
    assert "Test/Boundary" in results
    for item in results["Test/Boundary"]:
        # raw_data must be present when length-pool is applied
        assert item.raw_data is not None
        assert "length_limit" in item.raw_data
        limit = item.raw_data["length_limit"]
        assert (limit["min_length"], limit["max_length"]) in bounds
