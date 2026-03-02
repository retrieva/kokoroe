"""LLM の出力が安全かどうかの分類結果をまとめるスクリプト"""

import argparse
import logging

from auto_red_teaming_prompt.generators.summarizer import SafetySummarizer
from auto_red_teaming_prompt.utils.cli_logging import add_logging_args, init_logging_from_args
from auto_red_teaming_prompt.utils.common import initialize_llm
from auto_red_teaming_prompt.utils.reporter import ProgressReporter


def get_args():
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(description="Summarize LLM safety classification results.")
    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
        help="Path to the input JSON file containing LLM classification results.",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
        help="Path to the output JSON file to save the summary.",
    )
    parser.add_argument(
        "--model_type",
        type=str,
        default="vllm",
        help="Type of language model to use for generating summaries (default: vllm)",
    )
    parser.add_argument(
        "--model_config_file",
        type=str,
        required=True,
        help="Path to the model configuration file (JSON format).",
    )
    parser.add_argument(
        "--num_max_samples",
        type=int,
        default=2,
        help="Maximum number of examples to sample for qualitative summary (default: 2)",
    )
    # Logging options (common)
    add_logging_args(parser)
    parser.add_argument(
        "--progress_report",
        action="store_true",
        help="Enable progress reporting during summarization.",
    )

    return parser.parse_args()


def main():
    """安全性分類の結果をまとめるメイン関数。"""
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
    summarizer = SafetySummarizer(llm, reporter=reporter, num_max_samples=args.num_max_samples)

    classification_data = summarizer.load_data(args.input_file)
    summary_result = summarizer.generate_summary(classification_data)
    summarizer.save_results(summary_result, args.output_file)


if __name__ == "__main__":
    main()
