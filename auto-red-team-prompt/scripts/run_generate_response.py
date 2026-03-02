"""作成した攻撃的なプロンプトを LLM に渡して応答を生成するスクリプト"""

import argparse
import logging

from auto_red_teaming_prompt.generators.response import ResponseGenerator
from auto_red_teaming_prompt.utils.cli_logging import add_logging_args, init_logging_from_args
from auto_red_teaming_prompt.utils.common import initialize_llm
from auto_red_teaming_prompt.utils.reporter import ProgressReporter


def get_args():
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(description="Generate responses for Red Teaming prompts using LLM.")
    parser.add_argument(
        "--red_prompt_file",
        type=str,
        required=True,
        help="Path to the JSON file containing Red Teaming prompts.",
    )
    parser.add_argument(
        "--model_type",
        type=str,
        default="vllm",
        help="Type of language model to use (default: vllm)",
    )
    parser.add_argument(
        "--model_config_file",
        type=str,
        required=True,
        help="Path to the model configuration file (JSON format).",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="generated_responses.json",
        help="Path to save the generated responses (default: generated_responses.json)",
    )
    # Logging options (common)
    add_logging_args(parser)
    parser.add_argument(
        "--progress_report",
        action="store_true",
        help="Enable progress reporting during response generation.",
    )

    return parser.parse_args()


def main():
    """攻撃的なプロンプトに対する応答を生成し、結果を保存するメイン関数。"""
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
    generator = ResponseGenerator(llm, reporter=reporter)

    prompt_data = generator.load_data(args.red_prompt_file)
    output = generator.generate(prompt_data)
    generator.save_results(output, args.output_file)


if __name__ == "__main__":
    main()
