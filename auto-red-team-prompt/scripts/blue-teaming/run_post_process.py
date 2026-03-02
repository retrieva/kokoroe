"""Blue Teaming で作成した成果物をまとめるスクリプト.

以下のものをまとめる
- 学習データ
  - OpenAI API で DPO（Preference Tuning）が実施できる形式に変換
  - 学習データ件数
- 新規 Constitution
- Blue Teaming の参考にした攻撃成功率の統計情報
"""

import argparse
import logging

from auto_red_teaming_prompt.data import ConstitutionData
from auto_red_teaming_prompt.tools import BlueTeamingDataLoader, load_vulnerability_summary, write_blue_teaming_report
from auto_red_teaming_prompt.utils import load_json_data
from auto_red_teaming_prompt.utils.cli_logging import add_logging_args, init_logging_from_args


def get_args():
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(description="Blue Teaming Post-Process")
    parser.add_argument(
        "--training_data_path",
        type=str,
        required=True,
        help="Path to the JSON file containing training data.",
    )
    parser.add_argument(
        "--output_sft_data_path",
        type=str,
        default="sft_data.json",
        help="Path to save the SFT formatted training data (default: sft_data.json)",
    )
    parser.add_argument(
        "--output_dpo_data_path",
        type=str,
        default="dpo_data.json",
        help="Path to save the DPO formatted training data (default: dpo_data.json)",
    )
    parser.add_argument(
        "--constitution_path",
        type=str,
        required=True,
        help="Path to the Constitution file (JSON format).",
    )
    parser.add_argument(
        "--vulnerability_summary_path",
        type=str,
        required=True,
        help="Path to the JSON file containing vulnerability summary.",
    )
    parser.add_argument(
        "--output_report_path",
        type=str,
        default="blue_teaming_report.json",
        help="Path to save the Blue Teaming report (default: blue_teaming_report.json)",
    )
    # Logging options (common)
    add_logging_args(parser)

    return parser.parse_args()


def main():
    """Blue Teaming の後処理を実行"""
    args = get_args()

    level = init_logging_from_args(args)
    logging.getLogger(__name__).debug("Initialized logging with level %s", level)

    # Training data
    blue_teaming_data_loader = BlueTeamingDataLoader(args.training_data_path)
    sft_data_path = blue_teaming_data_loader.convert_to_sft_format(args.output_sft_data_path)
    dpo_data_path = blue_teaming_data_loader.convert_to_dpo_format(args.output_dpo_data_path)
    training_data_stats = blue_teaming_data_loader.compute_statistics()

    # Constitution の読み込み
    constitution_raw = load_json_data(args.constitution_path)
    constitution = ConstitutionData(**constitution_raw)

    # Vulnerability summary の読み込み
    vulnerability_summary = load_vulnerability_summary(args.vulnerability_summary_path)

    # Write
    write_blue_teaming_report(
        args.output_report_path,
        sft_data_path,
        dpo_data_path,
        training_data_stats,
        constitution,
        vulnerability_summary,
    )


if __name__ == "__main__":
    main()
