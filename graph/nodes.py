import asyncio
import logging

from core.state import ArticleState, EvaluatedArticleState, PipelineGraphState
from services.ingestion import fetch_all_rss_feeds
from services.db import get_existing_urls, save_articles
from core.utils import extract_clean_summary
from services.judge import evaluate_articles_batch

logger = logging.getLogger(__name__)


async def ingest_node(state: PipelineGraphState):
    """Ingest articles from RSS feeds and add them to the graph."""

    sources = state.get("sources", [])
    if not sources:
        logger.info("No sources provided for ingestion.")
        return {"raw_articles": []}

    # Fetch articles from RSS feeds
    try:
        result = await fetch_all_rss_feeds(sources, filter_days=7)
    except Exception as e:
        logger.error(f"Error occurred while fetching RSS feeds: {e}")
        return {"raw_articles": []}

    articles = result.get("articles", [])
    if not articles:
        logger.info("No articles found in the fetched feeds.")
        return {"raw_articles": []}

    # Extract incoming URLs and query DB via thread pool
    incoming_urls = [article["url"] for article in articles if "url" in article]
    existing_urls = await asyncio.to_thread(get_existing_urls, incoming_urls)

    # Filter out already existing articles
    new_articles = [
        article for article in articles if article.get("url") not in existing_urls
    ]

    logger.info(f"Fetched {len(new_articles)} new articles from RSS feeds.")
    return {"raw_articles": new_articles}


# Clean summary from HTML tags and unescape HTML entities
async def clean_node(state: PipelineGraphState):
    """Clean summaries and content of articles in the graph."""

    raw_articles: list[ArticleState] = state.get("raw_articles", [])
    if not raw_articles:
        logger.info("No raw articles to clean.")
        return {"raw_articles": []}

    cleaned_articles: list[ArticleState] = []
    for article in raw_articles:

        summary = article.get("summary")
        content = article.get("content")

        if not summary and not content:
            logger.warning(f"Article {article.get('url')} has no summary or content.")
            continue

        cleaned_summary = extract_clean_summary(
            summary, content
        )
        cleaned_article = {
            **article,
            "summary": cleaned_summary,
        }
        cleaned_articles.append(cleaned_article)

    logger.info(f"Cleaned {len(cleaned_articles)} articles.")
    return {"raw_articles": cleaned_articles}


async def judge_node(state: PipelineGraphState):
    """Evaluate articles against hype rules and add evaluation results to the graph."""
    raw_articles: list[ArticleState] = state.get("raw_articles", [])

    if not raw_articles:
        logger.info("No raw articles to evaluate.")
        return {"evaluated_articles": [], "failed_articles": []}

    # Evaluate articles against hype rules
    evaluated_articles, failed_articles = await evaluate_articles_batch(raw_articles)
    logger.info(
        f"Evaluated {len(evaluated_articles)} articles, {len(failed_articles)} articles failed to evaluate."
    )

    return {
        "raw_articles": [],
        "evaluated_articles": evaluated_articles,
        "failed_articles": failed_articles,
    }


async def save_node(state: PipelineGraphState):
    """Save evaluated articles to the database."""
    evaluated_articles: list[EvaluatedArticleState] = state.get(
        "evaluated_articles", []
    )
    if not evaluated_articles:
        logger.info("No evaluated articles to save.")
        return {"saved_articles_count": 0}

    logger.info(f"Saving {len(evaluated_articles)} evaluated articles to the database.")

    # Save articles to the database
    saved_count = 0
    try:
        saved_count = await asyncio.to_thread(save_articles, evaluated_articles)
        logger.info(f"Successfully saved {saved_count} articles to the database.")
    except Exception as e:
        logger.error(f"Error occurred while saving articles to the database: {e}")
        return {"saved_articles_count": 0, "db_error": str(e)}
    return {"saved_articles_count": saved_count}


async def report_node(state: PipelineGraphState):
    """Generate a final report based on the evaluation results."""

    evaluated_articles: list[EvaluatedArticleState] = state.get(
        "evaluated_articles", []
    )
    failed_articles: list[ArticleState] = state.get("failed_articles", [])

    if not evaluated_articles and not failed_articles:
        logger.info("No articles to report.")
        return {"final_report": "No articles to report."}

    db_error = state.get("db_error")

    total_evaluated = len(evaluated_articles)
    passed_count = sum(1 for a in evaluated_articles if a.get("is_passed"))
    rejected_count = total_evaluated - passed_count

    passed_pct = (passed_count / total_evaluated * 100) if total_evaluated else 0.0
    rejected_pct = (rejected_count / total_evaluated * 100) if total_evaluated else 0.0

    report_lines = [
        "## Pipeline Execution Summary",
        f"- Total Evaluated by LLM: {total_evaluated}",
        f"- Passed (Low Hype): {passed_count} ({passed_pct:.1f}%)",
        f"- Filtered Out (High Hype): {rejected_count} ({rejected_pct:.1f}%)",
        f"- Technical Failures (LLM/API): {len(failed_articles)}",
        f"- Successfully Persisted to DB: {state.get('saved_articles_count', 0)}",
        f"- Database Errors: {db_error if db_error else 'None'}",
    ]

    final_report = "\n".join(report_lines)
    logger.info(f"Pipeline report generated:\n{final_report}")

    return {"final_report": final_report}
