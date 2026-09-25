from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

hype_score_description = (
    "A numeric score from 1 to 10 evaluating promotional hype versus factual substance, "
    "strictly governed by 'violated_rule': "
    "1-3: Technical substance, open-source code/weights, model releases, benchmark results, or developer tools (must have violated_rule='NONE'). "
    "4-6: Legitimate industry news, business funding, executive commentary, or conceptual roadmaps with standard corporate PR tone (must have violated_rule='NONE'). "
    "7-10: Severe promotional hype, actionable marketing, unverified speculations, or clickbait (must correspond to an explicit non-NONE violation, scaling with severity)."
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
        description="A concise analysis evaluating the factual core, technical evidence, and promotional tone."
    )
    violated_rule: HypeRules = Field(
        description=(
            "The specific category of marketing violation detected. "
            "Must be 'NONE' for legitimate news, factual developments, and technical announcements. "
            "Specific guidelines: "
            "(1) Mentioning a conference or event is NOT an EVENT_PROMOTION unless it includes a direct call-to-action (ticket sales, registrations, discounts). "
            "(2) Technical terms, benchmark names, or architectural classes are NOT buzzwords unless used as empty superlatives without substance. "
            "(3) If a dramatic or provocative headline is backed by verified reporting, concrete research, or factual incidents in the content, do NOT classify it as CLICKBAIT_OR_GOSSIP."
            "Assign a non-NONE violation only when deceptive hype or pure marketing clearly dominates."
        )
    )
    hype_score: int = Field(ge=1, le=10, description=hype_score_description)