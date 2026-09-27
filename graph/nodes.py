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
    new_articles: list[ArticleState] = [
        article
        for article in articles
        if article.get("url") and article.get("url") not in existing_urls
    ]

    logger.info(f"Fetched {len(new_articles)} new articles from RSS feeds.")
    return {"raw_articles": new_articles}


# Clean summary from HTML tags and unescape HTML entities
async def preprocess_text_node(state: PipelineGraphState):
    """Clean summaries and content of articles in the graph."""

    raw_articles: list[ArticleState] = state.get("raw_articles", [])
    if not raw_articles:
        logger.info("No raw articles to clean.")
        return {"cleaned_articles": []}

    cleaned_articles: list[ArticleState] = []
    for article in raw_articles:

        summary = article["summary"]
        content = article.get("content", None)

        if not summary and not content:
            logger.warning(f"Article {article['url']} has no summary or content.")
            continue

        cleaned_summary = extract_clean_summary(summary, content)

        cleaned_article: ArticleState = {
            "url": article["url"],
            "title": article["title"],
            "summary": cleaned_summary,
            "source": article["source"],
            "date": article["date"],
        }

        cleaned_articles.append(cleaned_article)

    logger.info(f"Cleaned {len(cleaned_articles)} articles.")
    return {"cleaned_articles": cleaned_articles}


async def judge_node(state: PipelineGraphState):
    """Evaluate articles against hype rules and add evaluation results to the graph."""
    cleaned_articles: list[ArticleState] = state.get("cleaned_articles", [])

    if not cleaned_articles:
        logger.info("No cleaned articles to evaluate.")
        return {"evaluated_articles": [], "failed_articles": []}

    # Evaluate articles against hype rules
    evaluated_articles, failed_articles = await evaluate_articles_batch(
        cleaned_articles
    )
    logger.info(
        f"Evaluated {len(evaluated_articles)} articles, {len(failed_articles)} articles failed to evaluate."
    )

    return {
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
    """Generate the final briefing report containing passed articles and operational metrics."""
    evaluated_articles: list[EvaluatedArticleState] = state.get("evaluated_articles", [])
    failed_articles: list[ArticleState] = state.get("failed_articles", [])

    if not evaluated_articles and not failed_articles:
        logger.info("No articles to report.")
        return {"final_report": "No articles processed."}

    # 1.Filter out articles that passed the hype evaluation
    passed_articles = [
        article for article in evaluated_articles if article.get("is_passed")
    ]

    # 2. Calculate counts and percentages for reporting
    total_evaluated = len(evaluated_articles)
    passed_count = len(passed_articles)
    rejected_count = total_evaluated - passed_count
    passed_pct = (passed_count / total_evaluated * 100) if total_evaluated else 0.0
    rejected_pct = (rejected_count / total_evaluated * 100) if total_evaluated else 0.0

    report_sections: list[str] = [
        "# Daily Technical Briefing (De-Hype Feed)",
        f"*Curated {passed_count} high-signal articles out of {total_evaluated} total ingested.*",
        "\n---",
    ]

    # 3. Make a section for passed articles with their details
    if passed_articles:
        report_sections.append("## Curated Articles\n")
        for idx, article in enumerate(passed_articles, start=1):
            title = article.get("title", "Untitled")
            url = article.get("url", "#")
            score = article.get("hype_score", "N/A")
            reason = article.get("hype_reason", "No justification provided.")
            summary = article.get("summary", "").strip()

            article_block = (
                f"### {idx}. [{title}]({url})\n"
                f"- **Hype Score:** {score}/10\n"
                f"- **Signal Evaluation:** {reason}\n"
                f"- **Brief Summary:** {summary}\n"
            )
            report_sections.append(article_block)
    else:
        report_sections.append("## Curated Articles\n*No articles passed the technical substance threshold in this run.*\n")

    # 4. Wrap up with telemetry and operational metrics
    db_error = state.get("db_error")
    telemetry_block = (
        "---\n"
        "## Pipeline Execution Summary\n"
        f"- **Total Evaluated by LLM:** {total_evaluated}\n"
        f"- **Passed (Low Hype):** {passed_count} ({passed_pct:.1f}%)\n"
        f"- **Filtered Out (High Hype):** {rejected_count} ({rejected_pct:.1f}%)\n"
        f"- **Technical Failures (LLM/API):** {len(failed_articles)}\n"
        f"- **Successfully Persisted to DB:** {state.get('saved_articles_count', 0)}\n"
        f"- **Database Errors:** {db_error if db_error else 'None'}"
    )
    report_sections.append(telemetry_block)

    final_report = "\n".join(report_sections)
    logger.info("Pipeline report generated successfully.")

    return {"final_report": final_report}
