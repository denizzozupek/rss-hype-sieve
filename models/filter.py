from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

hype_score_description = (
    "A numeric score from 1 to 10 evaluating the marketing hype vs. technical substance: "
    "1-3 = Highly technical, grounded, contains code/benchmarks/concrete architecture; "
    "4-6 = Informative but contains minor buzzwords or light promotional framing; "
    "7-8 = Significant hype, unsubstantiated claims, or excessive buzzwords with little technical depth; "
    "9-10 = Pure marketing puffery, clickbait, or completely unverified revolutionary claims."
)

HypeRules = Literal[
    "none",
    "unsubstantiated_claims",
    "buzzword_stuffing",
    "pure_marketing",
]


class HypeEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hype_reason: str = Field(
        description="A brief explanation for the hype score assigned to the summary of articles"
    )
    violated_rule: HypeRules = Field(
        description=(
            "The primary category of hype detected. Use 'none' if the content is technically grounded. "
            "'unsubstantiated_claims' for bold metrics/breakthroughs without proof, "
            "'buzzword_stuffing' for heavy jargon without architecture/implementation, "
            "'pure_marketing' for promotional product announcements or waitlists."
        )
    )
    hype_score: int = Field(ge=1, le=10, description=hype_score_description)
