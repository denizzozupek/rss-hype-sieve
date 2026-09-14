from typing import TypedDict

from models.filter import HypeRules

class ArticleState(TypedDict):
    url: str
    title: str
    summary: str
    source: str

class FilteredArticleState(ArticleState):
    is_passed: bool
    hype_score: int
    hype_reason: str
    violated_rule: HypeRules

class PipelineGraphState(TypedDict):
    sources: list[str]
    raw_articles: list[ArticleState]    
    filtered_articles: list[FilteredArticleState]
    final_report: str

