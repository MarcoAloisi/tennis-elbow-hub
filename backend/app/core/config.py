"""Application configuration using Pydantic Settings.

This module provides centralized configuration management that:
- Loads settings from environment variables
- Validates types at startup
- Provides sensible defaults for development
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Tennis Tracker"
    app_env: str = "development"
    debug: bool = True

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS - stored as comma-separated string, parsed via property
    cors_origins_str: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins as a list."""
        if not self.cors_origins_str:
            return []
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    # Live Scores
    live_scores_url: str = ""
    score_refresh_interval: int = 10  # seconds

    # WebSocket
    ws_heartbeat_interval: int = 30  # seconds

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # File Upload
    max_upload_size_mb: int = 10

    @property
    def max_upload_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures settings are only loaded once
    and reused throughout the application lifecycle.
    """
    return Settings()
