from typing import TypedDict
from models.filter import HypeRules

class ArticleState(TypedDict):
    url: str
    title: str
    summary: str
    source: str
    date: str

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
    saved_articles_count: int

class IngestionBatchResult(TypedDict):
    articles: list[ArticleState]
    failed_sources: dict[str, str]
    total_fetched: int

