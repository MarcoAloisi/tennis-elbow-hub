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
    app_name: str = "Tennis Elbow Hub"
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
            if self.app_env.lower() == "development":
                return ["*"]
            return []  # Strict default for production
        origins = []
        for origin in self.cors_origins_str.split(","):
            origin = origin.strip()
            if not origin:
                continue
            if not origin.startswith(("http://", "https://")) and origin != "*":
                origins.append(f"https://{origin}")
            else:
                origins.append(origin)
        return origins

    # Live Scores
    live_scores_url: str = ""
    score_refresh_interval: int = 5  # seconds (changed from 10)

    # Database
    database_url: str | None = None  # Set by Render or use SQLite locally

    # Stats Tracking
    stats_timezone: str = "Europe/Rome"  # CEST for daily reset
    stats_checkpoint_interval: int = 300  # Save to DB every 5 minutes

    # Supabase (Storage, Outfits, Auth)
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""

    # WebSocket
    ws_heartbeat_interval: int = 30  # seconds

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # File Upload
    max_upload_size_mb: int = 3

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
