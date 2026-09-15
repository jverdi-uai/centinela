from fastapi import APIRouter

from centinela.core.tracing import metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def get_metrics() -> dict:
    return metrics()

