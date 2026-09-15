from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


Process = Literal["transaction", "document"]
Verdict = Literal[
    "aprobar", "validacion_adicional", "bloquear",
    "autentico", "sospechoso", "falso",
]


class Evidence(BaseModel):
    type: Literal["rule", "similarity", "vision", "metadata", "consistency"]
    name: str
    value: Any
    weight: float = Field(ge=0, le=1)
    detail: str
    region: dict[str, float] | None = None


class Decision(BaseModel):
    trace_id: str
    process: Process
    verdict: Verdict
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reasons: list[str]
    evidence: list[Evidence]
    requires_human_review: bool
    explanation_customer: str
    explanation_analyst: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0
    latency_ms: float = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    shadow: bool = False


class Feedback(BaseModel):
    trace_id: str
    label: Literal["fraude_confirmado", "legitimo", "documento_falso", "documento_autentico"]
    analyst: str = Field(min_length=2, max_length=120)
    comment: str = Field(default="", max_length=1000)

