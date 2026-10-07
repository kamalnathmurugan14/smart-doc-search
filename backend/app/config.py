"""Application settings: one class, read from backend/.env (see .env.example)."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    docs_root: Path = Path("./sample_docs")
    data_dir: Path = Path("./data")
    max_upload_mb: int = 25
    allowed_extensions: str = "pdf,docx,txt,md"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size_chars: int = 1000
    chunk_overlap_chars: int = 150
    hybrid_alpha: float = 0.5
    dup_near_threshold: float = 0.92
    dup_jaccard_min: float = 0.5
    cors_origins: str = "http://localhost:5173"
    tag_rules_path: Path = Path("./rules/tags.yaml")

    @field_validator("hybrid_alpha", "dup_near_threshold", "dup_jaccard_min")
    @classmethod
    def _unit_interval(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("must be between 0 and 1")
        return v

    @property
    def extensions(self) -> set[str]:
        return {e.strip().lower().lstrip(".") for e in self.allowed_extensions.split(",") if e.strip()}

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_path(self) -> Path:
        return self.data_dir / "index.sqlite"


@lru_cache
def get_settings() -> Settings:
    return Settings()
