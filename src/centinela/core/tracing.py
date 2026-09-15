from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from centinela.db import FeedbackRecord, TraceRecord, engine
from centinela.schemas.common import Decision, Feedback


def save_trace(decision: Decision, input_data: dict[str, Any], context: dict[str, Any], prompt_version: str) -> None:
    with Session(engine) as session:
        session.merge(TraceRecord(
            trace_id=decision.trace_id,
            process=decision.process,
            verdict=decision.verdict,
            score=decision.score,
            requires_human_review=decision.requires_human_review,
            shadow=decision.shadow,
            model=decision.model,
            tokens_in=decision.tokens_in,
            tokens_out=decision.tokens_out,
            cost_usd=decision.cost_usd,
            latency_ms=decision.latency_ms,
            prompt_version=prompt_version,
            input_json=input_data,
            output_json=decision.model_dump(mode="json"),
            context_json=context,
            created_at=decision.created_at,
        ))
        session.commit()


def list_traces(process: str | None = None, verdict: str | None = None, human_review: bool | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = select(TraceRecord).order_by(TraceRecord.created_at.desc()).limit(min(limit, 500))
    if process:
        query = query.where(TraceRecord.process == process)
    if verdict:
        query = query.where(TraceRecord.verdict == verdict)
    if human_review is not None:
        query = query.where(TraceRecord.requires_human_review == human_review)
    with Session(engine) as session:
        return [row.output_json for row in session.scalars(query)]


def trace_detail(trace_id: str) -> dict[str, Any] | None:
    with Session(engine) as session:
        row = session.get(TraceRecord, trace_id)
        if not row:
            return None
        feedback = list(session.scalars(select(FeedbackRecord).where(FeedbackRecord.trace_id == trace_id)))
        return {
            "decision": row.output_json,
            "input": row.input_json,
            "context": row.context_json,
            "prompt_version": row.prompt_version,
            "feedback": [
                {"label": item.label, "analyst": item.analyst, "comment": item.comment, "created_at": item.created_at.isoformat()}
                for item in feedback
            ],
        }


def save_feedback(feedback: Feedback) -> None:
    with Session(engine) as session:
        session.add(FeedbackRecord(**feedback.model_dump()))
        session.commit()


def metrics() -> dict[str, Any]:
    with Session(engine) as session:
        rows = list(session.scalars(select(TraceRecord)))
        feedback_count = session.scalar(select(func.count()).select_from(FeedbackRecord)) or 0
    if not rows:
        return {"total": 0, "by_process": {}, "by_verdict": {}, "human_review_rate": 0, "block_rate": 0, "latency_p50_ms": 0, "latency_p95_ms": 0, "cost_usd": 0, "cost_per_event_usd": 0, "feedback": feedback_count}
    latencies = sorted(row.latency_ms for row in rows)
    percentile = lambda p: latencies[min(len(latencies) - 1, round((len(latencies) - 1) * p))]
    by_process: dict[str, int] = {}
    by_verdict: dict[str, int] = {}
    for row in rows:
        by_process[row.process] = by_process.get(row.process, 0) + 1
        by_verdict[row.verdict] = by_verdict.get(row.verdict, 0) + 1
    total_cost = sum(row.cost_usd for row in rows)
    return {
        "total": len(rows),
        "by_process": by_process,
        "by_verdict": by_verdict,
        "human_review_rate": round(sum(row.requires_human_review for row in rows) / len(rows), 4),
        "block_rate": round(sum(row.verdict in {"bloquear", "falso"} for row in rows) / len(rows), 4),
        "latency_p50_ms": round(percentile(0.50), 2),
        "latency_p95_ms": round(percentile(0.95), 2),
        "cost_usd": round(total_cost, 8),
        "cost_per_event_usd": round(total_cost / len(rows), 8),
        "feedback": feedback_count,
    }

