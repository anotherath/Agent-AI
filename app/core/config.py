"""Settings đọc từ env (.env). Supabase chỉ dùng qua DATABASE_URL (Postgres)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = Field(
        default=None,
        validation_alias="DATABASE_URL",
        description="Postgres URI (Supabase transaction pooler).",
    )

    # Google OAuth (Authorization Code + PKCE)
    google_client_id: str | None = Field(default=None, validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(
        default=None,
        validation_alias="GOOGLE_CLIENT_SECRET",
    )
    google_redirect_uri: str | None = Field(
        default=None,
        validation_alias="GOOGLE_REDIRECT_URI",
    )

    # App session cookie (opaque token → hash in DB)
    session_cookie_name: str = Field(default="session", validation_alias="SESSION_COOKIE_NAME")
    session_ttl_days: int = Field(default=30, validation_alias="SESSION_TTL_DAYS")
    session_cookie_secure: bool = Field(
        default=False,
        validation_alias="SESSION_COOKIE_SECURE",
    )
    session_cookie_samesite: str = Field(
        default="lax",
        validation_alias="SESSION_COOKIE_SAMESITE",
    )

    # After Google callback
    auth_success_redirect_url: str | None = Field(
        default=None,
        validation_alias="AUTH_SUCCESS_REDIRECT_URL",
    )
    auth_error_redirect_url: str | None = Field(
        default=None,
        validation_alias="AUTH_ERROR_REDIRECT_URL",
    )

    oauth_transaction_ttl_minutes: int = Field(
        default=10,
        validation_alias="OAUTH_TRANSACTION_TTL_MINUTES",
    )

    # Comma-separated browser origins allowed to call the API with cookies.
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    @field_validator("session_cookie_samesite")
    @classmethod
    def _normalize_samesite(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def require_google_oauth(self) -> tuple[str, str, str]:
        if not self.google_client_id or not self.google_client_secret or not self.google_redirect_uri:
            raise RuntimeError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI in .env."
            )
        return (
            self.google_client_id,
            self.google_client_secret,
            self.google_redirect_uri,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
