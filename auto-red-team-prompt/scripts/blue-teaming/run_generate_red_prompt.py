"""Red Teaming の一環として、攻撃的なプロンプトを生成するスクリプトです。"""

import argparse
import logging

from auto_red_teaming_prompt.generators.red_prompt import RedPromptGenerator
from auto_red_teaming_prompt.models import MODELS
from auto_red_teaming_prompt.tools import load_vulnerability_summary, update_with_vulnerability_summary
from auto_red_teaming_prompt.utils.cli_logging import add_logging_args, init_logging_from_args
from auto_red_teaming_prompt.utils.common import initialize_llm


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
    parser.add_argument(
        "--severity_amplify_entity",
        type=int,
        default=10,
        help="Amplification factor for entity severity (default: 10)",
    )
    parser.add_argument(
        "--severity_amplify_scenario",
        type=int,
        default=4,
        help="Amplification factor for scenario severity (default: 4)",
    )
    parser.add_argument(
        "--vulnerability_summary",
        type=str,
        required=True,
        help="Path to the JSON file containing vulnerability summary.",
    )
    # Logging options (common)
    add_logging_args(parser)

    return parser.parse_args()


def main():
    """攻撃的なプロンプトを生成し、結果を保存するメイン関数です。"""
    args = get_args()

    # Configure logging for CLI
    level = init_logging_from_args(args)
    logging.getLogger(__name__).debug("Initialized logging with level %s", level)

    llm = initialize_llm(args.model_type, args.model_config_file)
    generator = RedPromptGenerator(
        llm,
        args.use_web_search,
        severity_amplify_entity=args.severity_amplify_entity,
        severity_amplify_scenario=args.severity_amplify_scenario,
    )

    risk_data, length_info = generator.load_risk_data(args.risk_json)
    vulnerability_summary = load_vulnerability_summary(args.vulnerability_summary)
    risk_data = update_with_vulnerability_summary(risk_data, vulnerability_summary)
    output = generator.generate((risk_data, length_info))
    generator.save_results(output, args.output_path)


if __name__ == "__main__":
    main()
