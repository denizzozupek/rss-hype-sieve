import feedparser
import re
import html
from datetime import datetime, timedelta

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


def _parse_date(entry: dict) -> datetime | None:
    time_struct = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
        or None
    )
    if time_struct:
        return datetime(*time_struct[:6])
    return None

def fetch_all_rss_feeds(sources: list[str], filter_days: int = 7) -> list[ArticleState]:
    """Fetches articles from all RSS feeds provided in the sources list."""

    articles: list[ArticleState] = []

    cutoff_date = datetime.now() - timedelta(days=filter_days)

    for source in sources:
        try:
            feed = feedparser.parse(source)
            for entry in feed.entries:

                entry_date = _parse_date(entry)
                if entry_date is None or entry_date < cutoff_date:
                    continue  # Skip articles that are too old or have no date

                final_summary = _clean_and_extract_summary(entry)

                article_state: ArticleState = {
                    "url": entry.get("link", "") or "",
                    "date": entry_date.strftime(datetime_format),
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
    print(f"Fetched {len(articles)} articles.")