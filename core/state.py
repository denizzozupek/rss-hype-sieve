from typing import TypedDict, NotRequired
from core.filter import HypeRules

class ArticleState(TypedDict):
    url: str
    title: str
    summary: str
    source: str
    date: str
    content: NotRequired[str | None]

class EvaluatedArticleState(ArticleState):
    is_passed: bool
    hype_score: int
    hype_reason: str
    violated_rule: HypeRules | None

class PipelineGraphState(TypedDict):
    sources: list[str]
    raw_articles: list[ArticleState]
    evaluated_articles: list[EvaluatedArticleState]
    failed_articles: list[ArticleState]
    cleaned_articles: list[ArticleState]
    final_report: str
    saved_articles_count: int
    db_error: str | None

class IngestionBatchResult(TypedDict):
    articles: list[ArticleState]
    failed_sources: dict[str, str]
    total_fetched: int

