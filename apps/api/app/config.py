from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    computer_use_model: str = "computer-use-preview"
    computer_use_max_steps: int = 4
    computer_use_navigation_timeout_ms: int = 45000
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    web_origin: str = "http://localhost:3000"
    web_origins: str | None = None
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def missing_env(self) -> list[str]:
        missing: list[str] = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_service_role_key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not self.web_origin:
            missing.append("WEB_ORIGIN")
        return missing

    @property
    def cors_origins(self) -> list[str]:
        defaults = {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        }
        configured = {self.web_origin.strip()} if self.web_origin else set()
        if self.web_origins:
            configured.update(origin.strip() for origin in self.web_origins.split(",") if origin.strip())
        return sorted(defaults | configured)

    @property
    def backend_mode(self) -> str:
        if self.has_openai and self.has_supabase:
            return "live"
        if self.has_openai:
            return "openai_without_supabase"
        if self.has_supabase:
            return "supabase_with_ai_fallback"
        return "local_fallback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
