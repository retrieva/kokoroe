"""LLM の応答が有害か安全かを評価するスクリプト"""

import argparse
import logging

from auto_red_teaming_prompt.generators.evaluator import ResponseEvaluator
from auto_red_teaming_prompt.utils.cli_logging import add_logging_args, init_logging_from_args
from auto_red_teaming_prompt.utils.common import initialize_llm
from auto_red_teaming_prompt.utils.reporter import ProgressReporter


def get_args():
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(description="Evaluate LLM responses for harmful or safe content.")
    parser.add_argument(
        "--evaluation_file",
        type=str,
        required=True,
        help="Path to the JSON file containing evaluation data.",
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
        default="evaluation_results.json",
        help="Path to save the evaluation results (default: evaluation_results.json)",
    )
    # Logging options (common)
    add_logging_args(parser)
    parser.add_argument(
        "--progress_report",
        action="store_true",
        help="Enable progress reporting during evaluation.",
    )

    return parser.parse_args()


def main():
    """LLM の応答を評価し、結果を保存するメイン関数です。"""
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
    evaluator = ResponseEvaluator(llm, reporter=reporter)

    evaluation_data = evaluator.load_data(args.evaluation_file)
    evaluation_result = evaluator.evaluate(evaluation_data)
    evaluator.save_results(evaluation_result, args.output_file)


if __name__ == "__main__":
    main()
