from fastapi import APIRouter, HTTPException, Query

from centinela.config import get_settings
from centinela.core.tracing import list_traces, save_feedback, trace_detail
from centinela.core.vector_store import SQLiteVectorStore
from centinela.schemas.common import Feedback

router = APIRouter(tags=["cases"])


@router.get("/cases")
def cases(
    process: str | None = None,
    verdict: str | None = None,
    requires_human_review: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    return list_traces(process, verdict, requires_human_review, limit)


@router.get("/cases/{trace_id}")
def case(trace_id: str) -> dict:
    result = trace_detail(trace_id)
    if not result:
        raise HTTPException(404, "Caso no encontrado")
    return result


@router.post("/feedback", status_code=201)
def feedback(payload: Feedback) -> dict[str, str]:
    detail = trace_detail(payload.trace_id)
    if not detail:
        raise HTTPException(404, "Caso no encontrado")
    save_feedback(payload)
    process = detail["decision"]["process"]
    kind = "transaction" if process == "transaction" else "document"
    canonical = detail["context"].get("canonical") or f"proceso={process}; score={detail['decision']['score']}; razones={','.join(detail['decision'].get('reasons', []))}"
    SQLiteVectorStore(get_settings()).add(payload.trace_id, kind, payload.label, canonical, {"analyst": payload.analyst})
    return {"status": "recorded", "trace_id": payload.trace_id}

