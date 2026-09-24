import html
import re


def clean_html_text(raw_text: str | None) -> str:
    """
    Cleans HTML tags, unescapes entities, and normalizes whitespace.
    Converts block tags to spaces first to prevent words from merging.
    """
    if not raw_text:
        return ""

    # 1. Replace block tags (p, br, div, li) with spaces to prevent words from merging
    text_with_spaces = re.sub(r"<(?:p|br|div|li)[^>]*>", " ", raw_text, flags=re.IGNORECASE)

    # 2. Strip all remaining HTML tags
    text_without_html = re.sub(r"<[^>]+>", "", text_with_spaces)

    # 3. Unescape HTML entities (&nbsp; -> space, &amp; -> &, &quot; -> ", etc.)
    unescaped_text = html.unescape(text_without_html)

    # 4. Normalize redundant whitespace and line breaks into a single space
    clean_text = re.sub(r"\s+", " ", unescaped_text).strip()

    return clean_text


def extract_first_meaningful_paragraph(raw_content: str | None, min_len: int = 80) -> str:
    """
    Extracts the first paragraph from HTML content that meets the minimum length threshold.
    Falls back to cleaned full content if no valid <p> block passes the threshold.
    """
    if not raw_content:
        return ""

    # Find all paragraph contents
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", raw_content, flags=re.IGNORECASE | re.DOTALL)

    for p in paragraphs:
        cleaned_p = clean_html_text(p)
        if len(cleaned_p) >= min_len:
            return cleaned_p

    # Fallback if no suitable <p> tag was found or matched the criteria
    return clean_html_text(raw_content)


def extract_clean_summary(
    raw_summary: str | None,
    raw_content: str | None = None,
    max_fallback_len: int = 350,
) -> str:
    """
    Returns cleaned summary if present. Otherwise, extracts the first meaningful
    paragraph from raw_content up to max_fallback_len.
    """
    clean_summary = clean_html_text(raw_summary)
    if clean_summary:
        return clean_summary

    if raw_content:
        meaningful_p = extract_first_meaningful_paragraph(raw_content)
        if meaningful_p:
            if len(meaningful_p) > max_fallback_len:
                return f"{meaningful_p[:max_fallback_len].strip()}..."
            return meaningful_p

    return "No summary available."