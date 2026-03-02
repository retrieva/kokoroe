"""Web検索を行い、その結果を要約する処理を定義します。"""

from langchain_classic.chains.summarize import load_summarize_chain
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.documents.base import Document
from langchain_core.language_models.base import BaseLanguageModel


def web_search_and_summarize(llm: BaseLanguageModel, query: str) -> str:
    """Web検索を行い、その結果を要約します。"""
    searcher = DuckDuckGoSearchRun()
    results = searcher.invoke(query)
    docs = [Document(page_content=results)]
    summarize_chain = load_summarize_chain(llm, chain_type="stuff")
    summary = summarize_chain.invoke(docs)
    return summary
