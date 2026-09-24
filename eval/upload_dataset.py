import json
import os
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()

DATASET_NAME = "ai-news-hype-eval"
DATASET_DESCRIPTION = "Hype/bias detection benchmark dataset for AI news summaries."
FILE_PATH = Path("data/ground_truth.json")


def upload_dataset() -> None:
    """Uploads ground truth examples to LangSmith using an idempotent bulk operation."""
    if not os.getenv("LANGCHAIN_API_KEY"):
        raise ValueError(
            "LANGCHAIN_API_KEY environment variable is missing. Check your .env file."
        )

    if not FILE_PATH.exists():
        raise FileNotFoundError(f"Dataset file not found: {FILE_PATH.resolve()}")

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    client = Client()

    # 1. Dataset existence check and creation
    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Existing dataset found: '{DATASET_NAME}' (ID: {dataset.id})")
    else:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=DATASET_DESCRIPTION,
        )
        print(f"Created new dataset: '{DATASET_NAME}' (ID: {dataset.id})")

    # 2. Idempotency check: avoid duplicate records
    existing_examples = list(client.list_examples(dataset_id=dataset.id))
    if existing_examples:
        print(
            f"Dataset already contains {len(existing_examples)} records. "
            "Skipping upload to prevent duplicate entries."
        )
        return

    # 3. Separate schema keys and perform bulk creation
    inputs = [item["inputs"] for item in records]
    outputs = [item["outputs"] for item in records]
    metadata = [item.get("metadata", {}) for item in records]

    client.create_examples(
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
        dataset_id=dataset.id,
    )

    print(
        f"Success: {len(records)} examples uploaded to dataset '{DATASET_NAME}'."
    )


if __name__ == "__main__":
    upload_dataset()