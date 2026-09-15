import html
import re


def clean_html_text(raw_text: str | None) -> str:
    """Cleans HTML tags and unescapes HTML entities from the given text."""
    if not raw_text:
        return ""
    
    text_without_html = re.sub(r"<[^>]+>", "", raw_text)
    unescaped_text = html.unescape(text_without_html)
    clean_text = re.sub(r"\s+", " ", unescaped_text).strip()
    return clean_text


def extract_clean_summary(
    raw_summary: str | None,
    raw_content: str | None = None,
    min_summary_len: int = 150,
    max_fallback_len: int = 350,
) -> str:
    """Cleans the summary and falls back to content if the summary is too short."""

    clean_summary = clean_html_text(raw_summary)
    clean_content = clean_html_text(raw_content)

    if len(clean_summary) < min_summary_len and clean_content:
        truncated = clean_content[:max_fallback_len].strip()
        return f"{truncated}..."

    return clean_summary or "No summary available."