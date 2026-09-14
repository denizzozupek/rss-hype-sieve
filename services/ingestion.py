import asyncio
import feedparser
import re
import html
from datetime import datetime

from core.config import DEFAULT_SOURCES, DEFAULT_JSON_SOURCES
from core.state import ArticleState

datetime_format = "%Y-%m-%d %H:%M:%S"


def _clean_and_extract_summary(entry: dict) -> str:
    # Extract the summary from the entry, if available and longer than 100 characters use it, otherwise use the content
    raw_content = ""
    content_list = entry.get("content", [])
    if content_list and isinstance(content_list, list) and len(content_list) > 0:
        raw_content = content_list[0].get("value", "")

    raw_summary = (
        entry.get("summary")
        or entry.get("description")
        or entry.get("subtitle")
        or entry.get("title")
        or ""
    )

    clean_summary = re.sub(r"<[^>]+>", "", raw_summary).strip()  # Remove HTML tags
    clean_content = re.sub(r"<[^>]+>", "", raw_content).strip()  # Remove HTML tags

    clean_summary = html.unescape(clean_summary)  # Unescape HTML entities
    clean_content = html.unescape(clean_content)  # Unescape HTML entities

    if len(clean_summary) < 150 and clean_content:
        return clean_content[:350] + "..."
    else:
        return clean_summary or "No summary available."


def _parse_date(entry: dict) -> str:
    time_struct = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
        or None
    )
    if time_struct:
        return datetime(*time_struct[:6]).strftime(datetime_format)
    return ""


def _filter_articles_by_date(articles: list[dict], filter_days: int) -> list[ArticleState]:
    """Filters articles based on the provided filter_days parameter."""
    if filter_days <= 0:
        return articles  # No filtering needed

    filtered_articles = []
    current_time = datetime.now()

    for article in articles:
        article_date_str = _parse_date(article)
        if article_date_str:
            try:
                article_date = datetime.strptime(article_date_str, datetime_format)
                delta = current_time - article_date
                if delta.days <= filter_days:
                    filtered_articles.append(article)
            except ValueError:
                print(f"Error parsing date for article: {article.get('title', 'Unknown title')}")

    return filtered_articles


def fetch_all_rss_feeds(sources: list[str], filter_days: int) -> list[ArticleState]:
    """Fetches articles from all RSS feeds provided in the sources list."""

    articles: list[ArticleState] = []

    for source in sources:
        try:
            feed = feedparser.parse(source)
            for entry in feed.entries:

                final_summary = _clean_and_extract_summary(entry)

                article_state: ArticleState = {
                    "url": entry.get("link", "") or "",
                    "date": _parse_date(entry),
                    "title": entry.get("title", "No title available."),
                    "summary": final_summary,
                    "source": source,
                }
                articles.append(article_state)

        except Exception as e:
            print(f"Error fetching articles from {source}: {e}")

    return articles


if __name__ == "__main__":
    # Example usage
    sources = DEFAULT_SOURCES  # Use the default sources defined in config
    articles = fetch_all_rss_feeds(sources)
    articles1 = articles[0]["date"]
    print(articles1)
