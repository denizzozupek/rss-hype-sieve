import asyncio
import logging

from langgraph.graph import MessageState, StateGraph
from core.state import ArticleState, FilteredArticleState, PipelineGraphState
from models.filter import HypeEvaluation
from services.ingestion import fetch_all_rss_feeds
from services.db import get_existing_urls, save_articles


async def ingest_node(state: PipelineGraphState):
    """Ingest articles from RSS feeds and add them to the graph."""

    if state["sources"] is None:
        logging.warning("No sources provided for ingestion.")
        return {"raw_articles": []}

    # Fetch articles from RSS feeds
    result = await fetch_all_rss_feeds(state["sources"], filter_days = 7)

    # Filter out articles that are already in the database
    new_articles: list[ArticleState] = []
    get_existing_urls_set = get_existing_urls([article["url"] for article in result["articles"]])
    for article in result["articles"]:
        if article["url"] not in get_existing_urls_set:
            new_articles.append(article)

    logging.info(f"Fetched {len(new_articles)} new articles from RSS feeds.")
    return {"raw_articles": new_articles}


async def save_node(state: PipelineGraphState):
    """Save filtered articles to the database."""
    filtered_articles: list[FilteredArticleState] = state.get("filtered_articles", [])
    if not filtered_articles:
        logging.info("No filtered articles to save.")
        return {"saved_articles_count": 0}

    logging.info(f"Saving {len(filtered_articles)} filtered articles to the database.")

    # Save articles to the database
    save_articles(filtered_articles)
    return {"saved_articles_count": len(filtered_articles)}
 