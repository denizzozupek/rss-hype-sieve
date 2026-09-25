from langsmith import aevaluate
from dotenv import load_dotenv
from services.judge import get_judge_chain

load_dotenv()
# Get the judge chain
judge_chain = get_judge_chain()

async def predict(inputs: dict) -> dict:
    """Evaluate the input using the judge chain and return the evaluation result."""

    # call the judge chain 
    result = await judge_chain.ainvoke(inputs)
    
    return result.model_dump(mode="json")


def hype_score_controls(outputs: dict , reference_outputs: dict) -> bool:
    """Check if the actual hype score is within the expected range."""
    
    expected_score = reference_outputs.get("expected_score")
    hype_score = outputs.get("hype_score")

    if expected_score is None or hype_score is None:
        return False
    
    return abs(expected_score - hype_score) <= 1


def hype_rule_controls(outputs: dict, reference_outputs: dict) -> bool:

    """Check if the actual violated rule matches the expected rule."""

    expected_rule = reference_outputs.get("expected_rule")
    violated_rule = outputs.get("violated_rule")

    if expected_rule is None or violated_rule is None:
        return False
    
    return expected_rule == violated_rule

async def run_evaluate():
    """Run the evaluation using LangSmith's aevaluate function."""
    experiment_results = await aevaluate(
        predict,
        data = "ai-news-hype-eval",
        evaluators = [hype_score_controls, hype_rule_controls],
        experiment_prefix = "ai_news_hype_evaluation",
        max_concurrency=4
    )
    df = experiment_results.to_pandas()
    
    cols = [
        "inputs.title",
        "reference.expected_rule",
        "outputs.violated_rule",
        "reference.expected_score",
        "outputs.hype_score",
        "feedback.hype_score_controls",
        "feedback.hype_rule_controls",
    ]
    
    # Filter the DataFrame to show only the rows where either of the control checks failed
    failed_mask = (df["feedback.hype_score_controls"] == False) | (df["feedback.hype_rule_controls"] == False)
    failed_df = df[failed_mask][cols]
    
    print("\n--- FAILED ROWS ---")
    print(failed_df.to_string(index=False))

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_evaluate())