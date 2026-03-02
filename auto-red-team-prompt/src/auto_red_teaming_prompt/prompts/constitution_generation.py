"""Constitution を生成する際に使用するプロンプトを定義。

Constitution は複数の文あるいは文書から構成されるため、リスト形式で保持する。
出力は json 形式で行う。
"""

import json
import re

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import PromptTemplate


class ConstitutionJSONOutputParser(BaseOutputParser[list[str]]):
    """Output parser that extracts Constitution items from LLM output in JSON format."""

    def parse(self, text: str) -> list[str]:
        """Parse the output text to extract Constitution items.

        Args:
            text: The output text from the LLM.

        Returns:
            The extracted Constitution items as a list.

        Raises:
            ValueError: If no Constitution items can be determined.

        """
        # ["Constitution 1", "Constitution 2"] の形式を取り出すための正規表現
        # 間に改行などが入ってもマッチするようにする
        json_pattern = r'\[\s*(?:"(?:\\.|[^"\\])*"(?:\s*,\s*"(?:\\.|[^"\\])*")*)?\s*\]'
        match = re.search(json_pattern, text, re.DOTALL)
        if not match:
            raise OutputParserException(f"Could not parse output: {text}")
        text = match.group(0)
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise OutputParserException(f"Could not parse output: {text}")
            return parsed
        except json.JSONDecodeError:
            raise OutputParserException(f"Could not parse output: {text}")

    @property
    def _type(self) -> str:
        return "constitution_json_parser"

    def get_format_instructions(self):
        """Get format instructions for the LLM prompt."""
        instructions = (
            'JSON形式で出力してください。例えば、以下のような形式です。\n["Constitution 1", "Constitution 2"]\n'
        )
        return instructions


constitution_parser = ConstitutionJSONOutputParser()

prompt_text = """既存の「AIの望ましい振る舞い」を記述したConstitutionを元に、新たなConstitutionを生成してください。
ただし、Constitutionを作成する際に、Red Teamingの結果を反映し、脆弱性を軽減するようなConstitutionを生成してください。
ここでのConstitutionは、AIの望ましい振る舞いについて、単文あるいは複数文を列挙したものとします。
また、Red Teamingの結果は、現在のAIの脆弱性を示すものであり、攻撃成功率などを踏まえて適切なConstitutionを生成してください。
なお、最初はConstitution作成の方針について短く説明を行い、その後にConstitutionを列挙してください。
{format_instructions}

[既存のConstitution]
{existing_constitution}

[Red Teamingの結果]
{red_teaming_results}
"""


PROMPT_GENERATE_CONSTITUTION = PromptTemplate(
    input_variables=["existing_constitution", "red_teaming_results"],
    template=prompt_text,
    partial_variables={"format_instructions": constitution_parser.get_format_instructions()},
)
