from fastapi import APIRouter

from centinela.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {"status": "ok", "mock_mode": settings.mock_mode, "shadow_mode": settings.shadow_mode, "version": settings.app_version}

