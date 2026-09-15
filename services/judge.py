import asyncio
import logging
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain.chat_models import init_chat_model

from prompts.llm_prompts import LLM_FILTER_PROMPT
from models.filter import HypeEvaluation
from core.state import FilteredArticleState, ArticleState

logger = logging.getLogger(__name__)

# Initialize the rate limiter and chat model with specified parameters
rate_limiter = InMemoryRateLimiter(max_calls=60, unit="minute")
model = init_chat_model(
    model_name="gpt-4o-mini", rate_limiter=rate_limiter, temperature=0.0, max_retries=3
)

structured_output = model.with_structured_output(HypeEvaluation)
chain = LLM_FILTER_PROMPT | structured_output


# =========== Functions for filtering articles ===========
async def filter_articles(
    title: str, summary: str, semaphore: asyncio.Semaphore
) -> HypeEvaluation:

    async with semaphore:
        logger.info(f"Filtering article: {title}")
        response = await chain.ainvoke({"title": title, "summary": summary})
        return response


# ========== Evaluate tasks in batches ==========
async def evaluate_articles_batch(
    articles: list[ArticleState], threshold_hype_score: int = 6, max_concurrent: int = 5
) -> tuple[list[FilteredArticleState], list[ArticleState]]:

    # Initialize lists to hold evaluated and non-evaluated articles
    evaluated_articles: list[FilteredArticleState] = []
    no_resulted_articles: list[ArticleState] = []

    # Limit the number of concurrent requests to avoid overwhelming the model
    semaphore = asyncio.Semaphore(max_concurrent)

    # 1. Create tasks for filtering articles concurrently
    logger.info(f"Evaluating batch of {len(articles)} articles")
    tasks = [
        filter_articles(article["title"], article["summary"], semaphore)
        for article in articles
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 2. Process the results and categorize articles based on evaluation outcome
    for article, result in zip(articles, results):

        # Handle exceptions and log errors for articles that failed to evaluate
        if isinstance(result, Exception):
            logger.error(
                f"Error occurred while filtering article '{article['title']}': {result}"
            )
            no_resulted_articles.append(article)

        # If the result is a valid HypeEvaluation, create a FilteredArticleState and append it to the evaluated articles list
        elif isinstance(result, HypeEvaluation):
            evaluated_article = FilteredArticleState(
                url=article["url"],
                title=article["title"],
                summary=article["summary"],
                source=article["source"],
                date=article["date"],
                is_passed=(result.hype_score <= threshold_hype_score),
                hype_score=result.hype_score,
                hype_reason=result.hype_reason,
                violated_rule=result.violated_rule,
            )
            evaluated_articles.append(evaluated_article)
            logger.info(
                f"Article '{article['title']}' appended to evaluated articles with score {result.hype_score}"
            )
        else:
            logger.warning(
                f"Unexpected result type for article '{article['title']}': {type(result)}"
            )
            no_resulted_articles.append(article)
    logger.info(
        f"Batch evaluation completed. Evaluated: {len(evaluated_articles)}, No Result: {len(no_resulted_articles)}"
    )
    return evaluated_articles, no_resulted_articles
