from typing import Literal

from pydantic import BaseModel, Field


class Review(BaseModel):
    label: str = Field(description='Response label exactly as given, e.g. "Response A"')
    accuracy: int = Field(description="Integer 1-5")
    completeness: int = Field(description="Integer 1-5")
    reasoning: int = Field(description="Integer 1-5, quality of logic")
    unsupported_claims: list[str] = Field(description="Claims that look wrong, unsupported or contradictory")
    missed: list[str] = Field(description="Important points the response left out")
    verdict: str = Field(description="One-sentence overall verdict")


class ReviewBatch(BaseModel):
    reviews: list[Review]


class FinalAnswer(BaseModel):
    answer: str = Field(description="The synthesized final answer")
    agreements: list[str] = Field(description="Points the panel agreed on (high confidence)")
    disagreements: list[str] = Field(description="Points of divergence and how they were resolved or why they remain open")
    confidence: Literal["low", "medium", "high"]
    confidence_rationale: str
    needs_human_review: bool
