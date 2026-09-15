DEFAULT_SOURCES: list[str] = [
"https://magazine.sebastianraschka.com/feed",
"https://importai.substack.com/feed",
"https://www.therundown.ai/feed",
"https://openai.com/news/rss.xml",
"https://lilianweng.github.io/index.xml",
"https://huggingface.co/blog/feed.xml",
"https://eugeneyan.com/rss/",
]

DEFAULT_JSON_SOURCES: list[str] = ["https://huggingface.co/api/daily_papers"]

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}
