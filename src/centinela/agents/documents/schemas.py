from typing import Any, Literal

from pydantic import BaseModel, Field

from centinela.schemas.common import Decision


DocumentType = Literal["cedula", "comprobante_domicilio", "contrato", "poder", "liquidacion", "firma", "otro"]


class ExtractedField(BaseModel):
    value: str
    confidence: float = Field(ge=0, le=1)


class Check(BaseModel):
    name: str
    status: Literal["pass", "fail", "warn", "pending"]
    detail: str
    critical: bool = False


class Finding(BaseModel):
    name: str
    confidence: float = Field(ge=0, le=1)
    detail: str
    region: dict[str, float] | None = None


class VisionExtraction(BaseModel):
    document_type: DocumentType
    fields: dict[str, ExtractedField]
    layout: str


class VisionForensics(BaseModel):
    manipulation_score: float = Field(ge=0, le=1)
    findings: list[Finding]


class DocumentReasoning(BaseModel):
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reasons: list[str]
    explanation_customer: str
    explanation_analyst: str


class DocumentDecision(Decision):
    document_type_detected: DocumentType
    fields: dict[str, ExtractedField]
    checks: list[Check]
    pages_analyzed: int
    image_quality: float = Field(ge=0, le=1)

