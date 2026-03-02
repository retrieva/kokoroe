"""Red Teaming の一環として、攻撃的なプロンプトを生成するスクリプトです。"""

import argparse
import logging

from auto_red_teaming_prompt.generators.red_prompt import RedPromptGenerator
from auto_red_teaming_prompt.models import MODELS
from auto_red_teaming_prompt.utils.cli_logging import add_logging_args, init_logging_from_args
from auto_red_teaming_prompt.utils.common import initialize_llm
from auto_red_teaming_prompt.utils.reporter import ProgressReporter


def get_args() -> argparse.Namespace:
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(description="Generate Red Teaming prompts.")
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
        "--risk_json",
        type=str,
        required=True,
        help="Path to the JSON file containing risk information.",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="output.json",
        help="Path to save the generated prompts (default: output.json)",
    )
    parser.add_argument(
        "--use_web_search",
        action="store_true",
        help="Use web search to gather additional information for prompt generation.",
    )
    # Logging options (common)
    add_logging_args(parser)
    parser.add_argument(
        "--progress_report",
        action="store_true",
        help="Enable progress reporting during prompt generation.",
    )

    return parser.parse_args()


def main():
    """攻撃的なプロンプトを生成し、結果を保存するメイン関数です。"""
    args = get_args()

    # Configure logging for CLI
    level = init_logging_from_args(args)
    logging.getLogger(__name__).debug("Initialized logging with level %s", level)

    reporter: ProgressReporter | None
    if args.progress_report:
        reporter = ProgressReporter()
    else:
        reporter = None
    llm = initialize_llm(args.model_type, args.model_config_file)
    generator = RedPromptGenerator(llm, args.use_web_search, reporter=reporter)

    risk_data = generator.load_risk_data(args.risk_json)
    output = generator.generate(risk_data)
    generator.save_results(output, args.output_path)


if __name__ == "__main__":
    main()
