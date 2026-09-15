from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Centinela Agents"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5.6-luna"
    openai_vision_model: str = "gpt-5.6-luna"
    openai_embedding_model: str = "text-embedding-3-small"
    mock_mode: bool = True
    shadow_mode: bool = False
    threshold_review: float = Field(default=0.35, ge=0, le=1)
    threshold_block: float = Field(default=0.70, ge=0, le=1)
    database_url: str = "sqlite:///data/centinela.db"
    trace_retention_days: int = Field(default=7, ge=1, le=365)
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    max_document_mb: int = Field(default=10, ge=1, le=50)
    max_pdf_pages: int = Field(default=5, ge=1, le=20)
    model_input_usd_per_million: float = 0.20
    model_output_usd_per_million: float = 1.20
    embedding_usd_per_million: float = 0.02
    transaction_rules_weight: float = 0.45
    transaction_similarity_weight: float = 0.25
    transaction_model_weight: float = 0.30
    document_vision_weight: float = 0.40
    document_checks_weight: float = 0.35
    document_model_weight: float = 0.25

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("threshold_block")
    @classmethod
    def validate_thresholds(cls, value: float, info):
        review = info.data.get("threshold_review", 0.35)
        if value <= review:
            raise ValueError("THRESHOLD_BLOCK debe ser mayor que THRESHOLD_REVIEW")
        return value

    @property
    def database_path(self) -> Path | None:
        prefix = "sqlite:///"
        return Path(self.database_url[len(prefix):]) if self.database_url.startswith(prefix) else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
