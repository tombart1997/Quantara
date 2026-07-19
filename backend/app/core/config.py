"""Application configuration, loaded from environment variables / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env lives at the repo root, one level above backend/.
    # extra="ignore": the root .env also holds POSTGRES_* keys used only by
    # docker-compose — they are not part of the app settings.
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Stored as a comma-separated string in .env; split on access.
    cors_origins: str = "http://localhost:4200"
    # Which market data provider implementation to use ("mock" for now).
    market_data_provider: str = "mock"

    # --- AI consultant (Kimi) ---------------------------------------------
    # Empty key = "prompt-only" mode: the API returns the generated prompt
    # for manual pasting. With a key, the backend calls Kimi directly.
    # Both Kimi platforms are OpenAI-compatible; see .env.example.
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.kimi.com/coding/v1"
    kimi_model: str = "kimi-for-coding"

    # Optional: Finnhub economic calendar (macro events). Free key at finnhub.io.
    finnhub_api_key: str = ""

    # --- Auto-refresh ------------------------------------------------------
    # Background loop keeping prices/events/news/signals current.
    refresh_enabled: bool = True
    refresh_interval_minutes: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed once per process."""
    return Settings()
