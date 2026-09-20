from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

hype_score_description = (
    "A numeric score from 1 to 10 evaluating marketing hype vs. informational substance: "
    "1-3 = Factual news, verified technical or business developments; "
    "4-6 = Newsworthy topic or release with acceptable promotional language; "
    "7-10 = High hype, pure PR, conference sales, or empty buzzwords."
)

HypeRules = Literal[
    "NONE",
    "EVENT_PROMOTION",
    "BUZZWORD_HEAVY",
    "UNVERIFIED_CLAIMS",
    "CLICKBAIT_OR_GOSSIP",
]


class HypeEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hype_reason: str = Field(
        description="A brief explanation justifying the assigned score and whether the article carries actual news value."
    )
    violated_rule: HypeRules = Field(
        description=(
            "The primary category of hype detected. "
            "Must be 'NONE' if the hype_score is 1-6. "
            "Use other categories ('EVENT_PROMOTION', 'BUZZWORD_HEAVY', 'UNVERIFIED_CLAIMS', 'CLICKBAIT_OR_GOSSIP') "
            "only when hype_score is 7 or higher."
        )
    )
    hype_score: int = Field(ge=1, le=10, description=hype_score_description)