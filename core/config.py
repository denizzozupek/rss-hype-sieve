from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

DEFAULT_SOURCES: list[str] = [
"https://magazine.sebastianraschka.com/feed",
"https://importai.substack.com/feed",
"https://www.therundown.ai/feed",
"https://openai.com/news/rss.xml",
"https://lilianweng.github.io/index.xml",
"https://huggingface.co/blog/feed.xml",
"https://eugeneyan.com/rss/",
]

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}

DEFAULT_DB_PATH = Path("db/hype_evaluations.db")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

