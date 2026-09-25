import asyncio
import json
from pathlib import Path
from services.ingestion import fetch_all_rss_feeds
from core.utils import clean_html_text, extract_clean_summary

EVAL_SOURCES = [
    "https://siliconangle.com/category/ai/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://simonwillison.net/atom/everything/",
    "https://www.marktechpost.com/feed/",
]

OUTPUT_FILE = Path("eval/ground_truth.json")


async def main():
    print("Example Evaluation Sample Fetcher is starting...")
    # Fetch articles from the specified sources with a filter of the last 14 days
    result = await fetch_all_rss_feeds(sources=EVAL_SOURCES, filter_days=14)

    articles = result.get("articles", [])
    print(f"Total articles fetched: {len(articles)}")

    # Ensure we have at least 4 articles per source, and limit to 4 samples per source
    samples_per_source = {}
    selected_samples = []

    for article in articles:
        src = article["source"]
        samples_per_source.setdefault(src, 0)

        if samples_per_source[src] < 4:
            samples_per_source[src] += 1
            selected_samples.append(
                {
                    "inputs": {
                        "title": clean_html_text(article.get("title")),
                        "summary": extract_clean_summary(
                            article.get("summary"),
                            article.get("content"),
                        ),
                    },
                    "outputs": {
                        "expected_score": None,
                        "expected_rule": None,
                    },
                    "metadata": {
                        "source": src,
                        "url": article.get("url", ""),
                    },
                }
            )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(selected_samples, f, ensure_ascii=False, indent=2)

    print(f"\nProcessing complete! {len(selected_samples)} samples saved to {OUTPUT_FILE}")
    print("Now open this file and label the 'null' fields.")


if __name__ == "__main__":
    asyncio.run(main())