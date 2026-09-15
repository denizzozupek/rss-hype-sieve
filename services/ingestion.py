import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, TypedDict

import feedparser
import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from core.config import DEFAULT_JSON_SOURCES, DEFAULT_SOURCES, DATETIME_FORMAT, RETRIABLE_STATUS_CODES
from core.state import ArticleState, IngestionBatchResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========== Network Layer  ===========

def _is_transient_error(exception: BaseException) -> bool:
    if isinstance(exception, (httpx.TransportError, httpx.TimeoutException)):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in RETRIABLE_STATUS_CODES
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_transient_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _fetch_url(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.get(url)
    response.raise_for_status()
    return response

# =========== Parsers ===========

def _parse_rss(content: str, source: str, cutoff_date: datetime) -> list[ArticleState]:
    feed = feedparser.parse(content)
    if getattr(feed, "bozo", 0) == 1 and not feed.entries:
        raise ValueError(f"Malformed feed: {feed.bozo_exception}")

    articles: list[ArticleState] = []
    for entry in feed.entries:
        link = entry.get("link", "").strip()
        time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if not link or not time_struct:
            continue

        entry_date = datetime(*time_struct[:6], tzinfo=timezone.utc)
        if entry_date < cutoff_date:
            continue

        summary = entry.get("summary") or entry.get("description") or ""
        articles.append(
            {
                "url": link,
                "title": entry.get("title", "No title available.").strip(),
                "summary": summary.strip(),
                "source": source,
                "date": entry_date.strftime(DATETIME_FORMAT),
            }
        )
    return articles


def _parse_hf_json(data: Any, source: str, cutoff_date: datetime) -> list[ArticleState]:
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list, got {type(data)}")

    articles: list[ArticleState] = []
    for item in data:
        paper = item.get("paper", {})
        paper_id = paper.get("id")
        entry_date_str = item.get("publishedAt", "")
        if not paper_id or not entry_date_str:
            continue

        try:
            entry_date = datetime.fromisoformat(entry_date_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if entry_date < cutoff_date:
            continue

        summary = paper.get("ai_summary") or item.get("summary") or ""
        articles.append(
            {
                "url": f"https://huggingface.co/papers/{paper_id}",
                "title": item.get("title", "No title available.").strip(),
                "summary": summary.strip(),
                "source": source,
                "date": entry_date.strftime(DATETIME_FORMAT),
            }
        )
    return articles


# =========== Generic Worker & Orchestrator ===========

async def _fetch_and_parse(
    client: httpx.AsyncClient,
    source: str,
    cutoff_date: datetime,
    parser: Callable[[Any, str, datetime], list[ArticleState]],
    is_json: bool = False,
) -> list[ArticleState]:
    response = await _fetch_url(client, source)
    payload = response.json() if is_json else response.text
    return parser(payload, source, cutoff_date)


async def fetch_all_sources(
    sources: list[str] | None = None,
    json_sources: list[str] | None = None,
    filter_days: int = 7,
) -> IngestionBatchResult:
    sources = sources or []
    json_sources = json_sources or []

    if not sources and not json_sources:
        logger.warning("No sources provided.")
        return {"articles": [], "failed_sources": {}, "total_fetched": 0}

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=filter_days)
    all_articles: list[ArticleState] = []
    failed_sources: dict[str, str] = {}
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)

    try:
        async with httpx.AsyncClient(timeout=15.0, limits=limits, follow_redirects=True) as client:
            tasks = [
                _fetch_and_parse(client, s, cutoff_date, _parse_rss, is_json=False)
                for s in sources
            ] + [
                _fetch_and_parse(client, s, cutoff_date, _parse_hf_json, is_json=True)
                for s in json_sources
            ]
            all_targets = sources + json_sources
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for target_url, result in zip(all_targets, results):
                if isinstance(result, Exception):
                    error_msg = f"{result.__class__.__name__}: {str(result)}"
                    failed_sources[target_url] = error_msg
                    logger.error(f"Failed {target_url}: {error_msg}")
                elif isinstance(result, list):
                    all_articles.extend(result)
                    logger.info(f"Fetched {len(result)} articles from {target_url}")

    except Exception as e:
        logger.critical(f"Critical pipeline failure: {e}")

    return {
        "articles": all_articles,
        "failed_sources": failed_sources,
        "total_fetched": len(all_articles),
    }


if __name__ == "__main__":
    result = asyncio.run(
        fetch_all_sources(sources=DEFAULT_SOURCES, json_sources=DEFAULT_JSON_SOURCES)
    )
    print(f"\n--- Ingestion Summary ---")
    print(f"Total: {result['total_fetched']} | Failed: {len(result['failed_sources'])}")