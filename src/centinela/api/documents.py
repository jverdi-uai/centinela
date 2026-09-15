import hashlib
import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from centinela.agents.documents import DocumentAgent, DocumentDecision
from centinela.agents.documents.schemas import DocumentType
from centinela.core.tracing import trace_detail

router = APIRouter(prefix="/documents", tags=["documents"])


@lru_cache
def get_agent() -> DocumentAgent:
    return DocumentAgent()


@router.post("/validate", response_model=DocumentDecision)
async def validate_document(
    file: UploadFile = File(...),
    document_type: DocumentType | None = Form(None),
    reference_id: str | None = Form(None),
    expected_fields: str | None = Form(None),
) -> DocumentDecision:
    content = await file.read()
    try:
        parsed_expected = json.loads(expected_fields) if expected_fields else None
        if parsed_expected is not None and not isinstance(parsed_expected, dict):
            raise ValueError("expected_fields debe ser un objeto JSON")
        return get_agent().evaluate({
            "filename": file.filename or "documento",
            "content": content,
            "document_type": document_type,
            "reference_id": reference_id,
            "expected_fields": parsed_expected,
        })
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/references")
async def register_reference(
    file: UploadFile = File(...),
    document_type: DocumentType = Form("firma"),
) -> dict[str, str]:
    content = await file.read()
    if not content:
        raise HTTPException(422, "El archivo está vacío")
    reference_id = "ref-" + hashlib.sha256(content).hexdigest()[:16]
    suffix = Path(file.filename or "reference.bin").suffix.lower()
    target = Path("data/references") / f"{reference_id}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    get_agent().vector_store.add(reference_id, "document", "documento_autentico", f"tipo={document_type}; referencia_registrada=true", {"path": str(target)})
    return {"reference_id": reference_id, "document_type": document_type}


@router.get("/{trace_id}/evidence")
def document_evidence(trace_id: str) -> dict[str, object]:
    detail = trace_detail(trace_id)
    if not detail or detail["decision"].get("process") != "document":
        raise HTTPException(404, "Caso documental no encontrado")
    evidence = detail["decision"].get("evidence", [])
    return {"trace_id": trace_id, "findings": [item for item in evidence if item.get("type") == "vision"]}

