"""Red Teamingの結果を要約するためのプロンプトを定義します。"""

from langchain_core.prompts import PromptTemplate

prompt_text = """以下の統計情報をもとに、Red Teaming の結果を日本語で要約してください。

[統計情報/定量的な結果]
{quantitative_stats}
"""


PROMPT_RED_TEAMING_SUMMARY = PromptTemplate(
    input_variables=["quantitative_stats"],
    template=prompt_text,
)
