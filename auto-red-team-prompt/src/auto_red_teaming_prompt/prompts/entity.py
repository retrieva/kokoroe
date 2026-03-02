"""エンティティを作成するためのプロンプトを定義します。"""

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field


class EntityFormat(BaseModel):
    """生成されるエンティティのフォーマット"""

    entities: list[str] = Field(
        description="カテゴリに関連する固有名詞のリスト",
    )


instruction_parser = PydanticOutputParser(pydantic_object=EntityFormat)

prompt_text = """カテゴリ「{category}」に関連する代表的な固有名詞を日本語で{n_entity}個挙げてください。
{format_instructions}
"""

PROMPT_ENTITY = PromptTemplate(
    input_variables=["category", "n_entity", "format_instructions"],
    template=prompt_text,
).partial(format_instructions=instruction_parser.get_format_instructions())
