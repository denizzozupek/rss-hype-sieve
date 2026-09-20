import asyncio
import logging
from core.state import PipelineGraphState
from services.db import db_init
from graph.pipeline import create_pipeline_graph
from core.config import OPENAI_API_KEY, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():

    initial_state: PipelineGraphState = {"sources": ["https://techcrunch.com/feed/"]}

    # Initialize the database
    try:
        await asyncio.to_thread(db_init, DEFAULT_DB_PATH)
    except Exception as e:
        logger.error(f"Failed to initialize the database: {e}")
        return

    # Create the pipeline graph
    try:
        pipeline_graph = create_pipeline_graph()
    except Exception as e:
        logger.error(f"Failed to create the pipeline graph: {e}")
        return

    # Execute the pipeline graph
    try:
        final_state = await pipeline_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Failed to execute the pipeline graph: {e}")
        return

    return {"status": "success", "final_state": final_state["final_report"]}

if __name__ == "__main__":
    asyncio.run(main())