import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Collection

from core.state import EvaluatedArticleState

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("db/hype_evaluations.db")


def db_init(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    target_path = Path(db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(target_path, timeout=10.0)) as conn:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hype_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_passed BOOLEAN DEFAULT NULL,
                    hype_score INTEGER DEFAULT NULL CHECK(hype_score BETWEEN 1 AND 10),
                    hype_reason TEXT DEFAULT NULL,
                    violated_rule TEXT DEFAULT NULL
                )
                """)
    logger.info("Database initialized successfully at %s", target_path)


def get_existing_urls(
    urls: Collection[str], db_path: Path | str = DEFAULT_DB_PATH
) -> set[str]:
    if not urls:
        return set()

    placeholders = ", ".join("?" for _ in urls)
    query = f"SELECT url FROM hype_evaluations WHERE url IN ({placeholders})"

    with closing(sqlite3.connect(db_path, timeout=10.0)) as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(urls))
        return {row[0] for row in cursor.fetchall()}


def save_articles(
    articles: list[EvaluatedArticleState], db_path: Path | str = DEFAULT_DB_PATH
) -> int:
    if not articles:
        logger.info("No articles to save.")
        return 0
    with closing(sqlite3.connect(db_path, timeout=10.0)) as conn:
        with conn:
            records = [(article["url"], article["title"], article["source"], article.get("summary"), article.get("is_passed"), article.get("hype_score"), article.get("hype_reason"), article.get("violated_rule")) for article in articles]
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO hype_evaluations 
                (url, title, source, summary, is_passed, hype_score, hype_reason, violated_rule)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
        return len(records)