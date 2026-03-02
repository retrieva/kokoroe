"""Blue Teaming で作成したデータ周りを整えるスクリプト"""

import json
import os

from auto_red_teaming_prompt.data import (
    BlueTeamingTrainData,
    ConstitutionData,
    OutputPrompt,
    OutputResponse,
    RedTeamingResultForBlueTeaming,
)
from auto_red_teaming_prompt.utils import load_json_data, save_json_data


class BlueTeamingDataLoader:
    """Blue Teaming のデータを読み込み、OpenAI フォーマットに変換するクラス"""

    def __init__(self, data_path: str):
        """Initialize the data loader."""
        if not os.path.isfile(data_path):
            raise FileNotFoundError(f"Data file not found: {data_path}")
        self.data_path = data_path
        self.data = self.load_data()

    def load_data(self) -> dict[str, list[BlueTeamingTrainData]]:
        """JSON ファイルからデータを読み込む"""
        data = load_json_data(self.data_path)

        formatted_data: dict[str, list[BlueTeamingTrainData]] = {}
        for category, items in data.items():
            formatted_data[category] = []
            for item in items:
                formatted_data[category].append(
                    BlueTeamingTrainData(
                        input=OutputPrompt(**item["input"]),
                        improved_response=OutputResponse(**item["improved_response"]),
                        output=OutputResponse(**item["output"]),
                    )
                )
        return formatted_data

    def convert_to_sft_format(self, output_path: str) -> str:
        """データを SFT (Supervised Fine-Tuning; OpenAI) フォーマットに変換して保存する"""
        sft_format_data: list[dict] = []
        for _, items in self.data.items():
            for item in items:
                input_prompt: OutputPrompt = item["input"]
                improved_response: OutputResponse = item["improved_response"]
                sft_format_data.append(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": input_prompt.prompt,
                            },
                            {
                                "role": "assistant",
                                "content": improved_response.response_text,
                            },
                        ]
                    }
                )

        with open(output_path, "w", encoding="utf-8") as f:
            for entry in sft_format_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return output_path

    def convert_to_dpo_format(self, output_path: str) -> str:
        """データを DPO (OpenAI) フォーマットに変換して保存する"""
        dpo_format_data: list[dict] = []
        for _, items in self.data.items():
            for item in items:
                input_prompt: OutputPrompt = item["input"]
                improved_response: OutputResponse = item["improved_response"]
                negative_response: OutputResponse = item["output"]
                dpo_format_data.append(
                    {
                        "input": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": input_prompt.prompt,
                                }
                            ]
                        },
                        "preferred_output": [
                            {
                                "role": "assistant",
                                "content": improved_response.response_text,
                            }
                        ],
                        "non_preferred_output": [
                            {
                                "role": "assistant",
                                "content": negative_response.response_text,
                            }
                        ],
                    }
                )

        with open(output_path, "w", encoding="utf-8") as f:
            for entry in dpo_format_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return output_path

    def compute_statistics(self) -> dict[str, dict[str, int]]:
        """データの統計情報を計算する

        ここでは、単純に学習データの件数（総数、カテゴリごとの数）を計算します。
        """
        num_samples = sum(len(items) for items in self.data.values())
        category_counts = {category: {"num-examples": len(items)} for category, items in self.data.items()}

        category_counts["overall"] = {"num-examples": num_samples}

        return category_counts


def write_blue_teaming_report(
    output_path: str,
    sft_data_path: str,
    dpo_data_path: str,
    training_data_stats: dict[str, int],
    constitution: ConstitutionData,
    vulnerability_summary: dict[str, RedTeamingResultForBlueTeaming],
) -> None:
    """Blue Teaming の情報を json ファイルとして保存する"""
    output_data = {
        "training-data": {
            "sft_data_path": sft_data_path,
            "dpo_data_path": dpo_data_path,
        },
        "training-data-stats": training_data_stats,
        "artifacts": {
            "created-llm-constitutions": constitution.texts,
            "vulnerability-summary": {
                category: {
                    "number-of-successes": stats["vulnerability_stats"].number_of_successes,
                    "number-of-attacks": stats["vulnerability_stats"].number_of_attacks,
                    "success-rate": stats["vulnerability_stats"].success_rate,
                    "severity": stats["severity"],
                }
                for category, stats in vulnerability_summary.items()
            },
        },
    }

    save_json_data(output_data, output_path)
