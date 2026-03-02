"""詳細な攻撃シナリオを生成するためのプロンプトを定義します。"""

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field


class DetailAttackScenarioFormat(BaseModel):
    """生成される攻撃シナリオのフォーマット"""

    scenarios: list[str] = Field(
        description="攻撃シナリオの詳細な説明",
    )


instruction_parser = PydanticOutputParser(pydantic_object=DetailAttackScenarioFormat)


prompt_text = """カテゴリ「{category}」に関連する具体的な攻撃内容を日本語で{n_scenario}個挙げてください。
{format_instructions}
"""

PROMPT_SCENARIO = PromptTemplate(
    input_variables=["category", "n_scenario", "format_instructions"],
    template=prompt_text,
).partial(format_instructions=instruction_parser.get_format_instructions())
