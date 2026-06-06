from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / "apps/api" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    web_origin: str = "http://localhost:3000"
    openai_api_key: str | None = None
    openai_research_model: str = "gpt-4.1-mini"
    supabase_db_url: str | None = None
    database_url: str | None = None

    @property
    def db_url(self) -> str | None:
        return self.supabase_db_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
