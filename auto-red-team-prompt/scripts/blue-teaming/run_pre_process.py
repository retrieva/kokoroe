"""Blue Teaming の前処理を実施

- 既存の Constitution に対し、Red Teaming の結果を反映した新しい Constitution を生成
- カテゴリごとに重要性と Red Teaming の攻撃成功率をまとめる
"""

import argparse
import logging

from auto_red_teaming_prompt.generators.constitution import ConstitutionGenerator
from auto_red_teaming_prompt.models import MODELS
from auto_red_teaming_prompt.tools import save_vulnerability_summary, summarize_vulnerabilities
from auto_red_teaming_prompt.utils.cli_logging import add_logging_args, init_logging_from_args
from auto_red_teaming_prompt.utils.common import initialize_llm


def get_args():
    """コマンドライン引数のパース"""
    parser = argparse.ArgumentParser(description="Blue Teaming Pre-Process")
    parser.add_argument(
        "--model_type",
        type=str,
        default="vllm",
        help="Type of language model to use (default: vllm)",
        choices=list(MODELS.keys()),
    )
    parser.add_argument(
        "--model_config_file",
        type=str,
        required=True,
        help="Path to the model configuration file (JSON format).",
    )
    parser.add_argument(
        "--input_data",
        type=str,
        required=True,
        help="Path to the JSON file containing input data for processing.",
    )
    parser.add_argument(
        "--constitution_output_path",
        type=str,
        default="updated_constitution.json",
        help="Path to save the updated constitution (default: updated_constitution.json)",
    )
    parser.add_argument(
        "--summary_output_path",
        type=str,
        default="vulnerability_summary.json",
        help="Path to save the vulnerability summary (default: vulnerability_summary.json)",
    )
    add_logging_args(parser)
    return parser.parse_args()


def main():
    """Blue Teaming の前処理を実行"""
    args = get_args()

    level = init_logging_from_args(args)
    logging.getLogger(__name__).debug("Initialized logging with level %s", level)

    llm = initialize_llm(args.model_type, args.model_config_file)
    generator = ConstitutionGenerator(llm)
    loaded_input = generator.load_data(args.input_data)
    updated_constitution = generator.generate(loaded_input)
    generator.save_results(updated_constitution, args.constitution_output_path)

    vulnerability_summary = summarize_vulnerabilities(loaded_input)
    save_vulnerability_summary(vulnerability_summary, args.summary_output_path)


if __name__ == "__main__":
    main()
