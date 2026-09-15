import asyncio
import logging

from langgraph.graph import MessageState, StateGraph
from core.state import ArticleState, FilteredArticleState, PipelineGraphState
from models.filter import HypeEvaluation
from services.ingestion import fetch_all_rss_feeds
from services.db import is_article_in_db, save_article


async def ingest_node(state: PipelineGraphState):
    """Ingest articles from RSS feeds and add them to the graph."""

    if state["sources"] is None:
        logging.warning("No sources provided for ingestion.")
        return {"raw_articles": []}

    # Fetch articles from RSS feeds
    raw_articles = await fetch_all_rss_feeds(state["sources"], filter_days = 7)

    # Filter out articles that are already in the database
    new_articles: list[ArticleState] = []
    for article in raw_articles:
        if not is_article_in_db(article["url"]):
            new_articles.append(article)
            save_article(article)
    


  