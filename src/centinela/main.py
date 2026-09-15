import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from centinela.api import cases, documents, health, metrics, transactions
from centinela.config import get_settings
from centinela.db import init_db


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        Path("openapi.json").write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Agentes explicables para evaluación de transacciones y validación documental.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=r"https?://localhost(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(transactions.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(cases.router, prefix=prefix)
    app.include_router(metrics.router, prefix=prefix)

    web_dir = Path(__file__).parent / "web"
    app.mount("/assets", StaticFiles(directory=web_dir), name="assets")

    @app.get("/", tags=["app"])
    def root() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


app = create_app()
