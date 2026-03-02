"""データ関連に関するユーティリティ関数とデータクラスを定義します。"""

import json
from typing import Optional, TypedDict

from pydantic.dataclasses import dataclass


@dataclass
class TargetRisk:
    """リスク情報を保持するデータクラス。"""

    category: str
    description: str
    severity: int | float
    examples: Optional[list[str]] = None


@dataclass
class OutputPrompt:
    """生成されたプロンプトの出力を保持するデータクラス。"""

    category: str
    prompt: str
    raw_data: Optional[dict] = None


@dataclass
class LengthLimit:
    """プロンプトの長さ制限を保持するデータクラス。"""

    max_length: int
    min_length: int


@dataclass
class OutputResponse:
    """生成された応答の出力を保持するデータクラス。"""

    response_text: Optional[str]
    response_status: str
    optional_data: Optional[dict] = None


@dataclass
class SafetyClassificationResult:
    """安全性分類の結果を保持するデータクラス。"""

    classification_label: str | None
    raw_output: Optional[str] = None


@dataclass
class SafetyClassificationQuantitativeStats:
    """安全性分類の定量的統計情報を保持するデータクラス。"""

    number_of_successes: int
    number_of_attacks: int
    success_rate: float


@dataclass
class SafetyClassificationQualitativeStats:
    """安全性分類の定性的統計情報を保持するデータクラス。"""

    attack_success_examples: list[dict[str, str]]
    guard_success_examples: list[dict[str, str]]


@dataclass
class ConstitutionData:
    """Constitutionに関するデータを保持するデータクラス。"""

    texts: list[str]


class Responses(TypedDict):
    """ResponseImproverの出力データの型定義。"""

    input: OutputPrompt
    output: OutputResponse


@dataclass
class ResponseImproverInput:
    """ResponseImproverの入力データを保持するデータクラス。"""

    responses: dict[str, list[Responses]]
    constitution: ConstitutionData


class RedTeamingResultForBlueTeaming(TypedDict):
    """Blue Teamingの前処理で使用するRed Teamingの結果を保持するTypedDict。"""

    vulnerability_stats: SafetyClassificationQuantitativeStats
    severity: int | float


class ConstitutionInput(TypedDict):
    """ConstitutionGeneratorの入力データの型定義。"""

    current_constitution: ConstitutionData
    red_teaming_results: dict[str, SafetyClassificationQuantitativeStats]
    attack_scenario: list[TargetRisk]


class BlueTeamingTrainData(TypedDict):
    """Blue Teamingの学習データの型定義。"""

    input: OutputPrompt
    improved_response: OutputResponse
    output: OutputResponse


def load_risk(risk_json: str) -> tuple[list[TargetRisk], Optional[list[LengthLimit]]]:
    """リスク情報をJSONファイルから読み込みます。"""
    with open(risk_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    attack_scenarios = data.get("attack-scenario")
    if not attack_scenarios:
        raise ValueError("No attack scenarios found in the JSON file.")
    target_risks = [TargetRisk(**item) for item in attack_scenarios]

    length_pool = data.get("other-conditions", {}).get("length-pool", None)
    if length_pool:
        length_pool = [LengthLimit(min_length=item["min"], max_length=item["max"]) for item in length_pool]
    else:
        length_pool = None

    return target_risks, length_pool


def load_red_prompt(red_prompt_file: str) -> dict[str, list[OutputPrompt]]:
    """指定されたファイルからRed Teamingプロンプトを読み込みます。"""
    with open(red_prompt_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    output = {}
    for category, prompts in data.items():
        output[category] = [OutputPrompt(**prompt) for prompt in prompts]

    return output
