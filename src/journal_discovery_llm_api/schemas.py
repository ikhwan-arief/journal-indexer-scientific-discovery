from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


ALLOWED_MATCHED_FIELDS = ("title", "categories", "areas", "subject_area")


class AbstractCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceid: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=600)
    categories: str | None = Field(default=None, max_length=2400)
    areas: str | None = Field(default=None, max_length=2400)
    subject_area: str | None = Field(default=None, max_length=1200)
    publisher: str | None = Field(default=None, max_length=600)
    country: str | None = Field(default=None, max_length=200)
    lexical_score: float = Field(default=0.0, ge=0.0, le=1_000_000.0)


class AbstractMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_text: str = Field(..., min_length=1, max_length=20000)
    top_n: int = Field(default=50, ge=1, le=50)
    candidates: list[AbstractCandidate] = Field(..., min_length=1, max_length=50)


class RankedCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceid: str = Field(..., min_length=1, max_length=128)
    rank: int = Field(..., ge=1, le=50)
    llm_score: int = Field(..., ge=0, le=100)
    rationale: str = Field(default="", max_length=240)
    matched_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class AbstractMatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = Field(..., min_length=1, max_length=32)
    model: str = Field(..., min_length=1, max_length=200)
    latency_ms: int = Field(..., ge=0)
    ranked: list[RankedCandidate] = Field(default_factory=list)


class ProviderScoredCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceid: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=600)
    lexical_score: float = Field(default=0.0, ge=0.0)
    llm_score: int = Field(default=0, ge=0, le=100)
    rationale: str = Field(default="", max_length=240)
    matched_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

