"""LLM の回答に対して、Constitution を用いて改善を行うモジュール。"""

import json
import re

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import PromptTemplate


class ResponseImprovementParser(BaseOutputParser[str]):
    """Output parser that extracts improved response from LLM output using regex."""

    def parse(self, text: str) -> str:
        """Parse the output text to extract the improved response.

        Args:
            text: The output text from the LLM.

        Returns:
            The extracted improved response.

        Raises:
            ValueError: If the improved response cannot be determined.

        """
        OUTPUT_KEY = "improved_response"

        # json でパースを行う
        # LLM の出力は text + json 形式であることが多いので、json 部分を抜き出す
        json_pattern = r'\{\s*"improved_response"\s*:\s*"((?:\\.|[^"\\])*)"\s*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if not match:
            raise OutputParserException(f"Could not parse output: {text}")
        text = match.group(0)
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict) or OUTPUT_KEY not in parsed:
                raise OutputParserException(f"Could not parse output: {text}")
            return parsed[OUTPUT_KEY]
        except json.JSONDecodeError:
            raise OutputParserException(f"Could not parse output: {text}")

    @property
    def _type(self) -> str:
        return "response_improvement_parser"

    def get_format_instructions(self):
        """Get format instructions for the LLM prompt."""
        instructions = (
            'JSON形式で出力してください。その際、改善した回答を "improved_response" というキーで出力してください。例えば、以下のような形式です。\n'
            '{"improved_response": "改善された回答"}\n'
        )
        return instructions


response_improvement_parser = ResponseImprovementParser()

prompt_text = """AIアシスタントの回答について、「AIの望ましい振る舞い」を記述したConstitutionを考慮した上で、より良い回答を生成してください。
補足情報として、AIアシスタントへの入力も提供されます。
{format_instructions}

[AIアシスタントへの入力]
{prompt}

[AIアシスタントの回答]
{response}

[Constitution]
{constitution}
"""

PROMPT_RESPONSE_IMPROVE = PromptTemplate(
    input_variables=["prompt", "response", "constitution"],
    template=prompt_text,
).partial(format_instructions=response_improvement_parser.get_format_instructions())
