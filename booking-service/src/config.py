"""Configuración centralizada para Booking Service."""
from functools import lru_cache
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------
    # Database
    # -------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://estetica:estetica@postgres:5432/estetica",
        validation_alias="DATABASE_URL",
    )

    # -------------------------------------------
    # Internal API Key (auth entre servicios)
    # -------------------------------------------
    internal_api_key: str = Field(
        default="dev-internal-key-change-in-prod",
        validation_alias="INTERNAL_API_KEY",
    )

    # -------------------------------------------
    # Google Calendar / Gmail
    # -------------------------------------------
    google_client_id: Optional[str] = Field(default=None, validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, validation_alias="GOOGLE_CLIENT_SECRET")
    google_refresh_token: Optional[str] = Field(default=None, validation_alias="GOOGLE_REFRESH_TOKEN")
    google_calendar_id: str = Field(default="primary", validation_alias="GOOGLE_CALENDAR_ID")

    # -------------------------------------------
    # Email
    # -------------------------------------------
    email_from: str = Field(default="noreply@ayudio.cl", validation_alias="EMAIL_FROM")
    email_provider_key: Optional[str] = Field(default=None, validation_alias="EMAIL_PROVIDER_KEY")
    admin_email: str = Field(..., validation_alias="ADMIN_EMAIL")

    # -------------------------------------------
    # Configuración de Negocio
    # -------------------------------------------
    timezone: str = Field(default="America/Santiago", validation_alias="TIMEZONE")
    cancel_min_hours: int = Field(default=24, validation_alias="CANCEL_MIN_HOURS")
    booking_max_horizon_days: int = Field(default=60, validation_alias="BOOKING_MAX_HORIZON_DAYS")
    grid_size_minutes: int = Field(default=15, validation_alias="GRID_SIZE_MINUTES")
    max_active_bookings_per_client: int = Field(default=3, validation_alias="MAX_ACTIVE_BOOKINGS_PER_CLIENT")

    # -------------------------------------------
    # Logging
    # -------------------------------------------
    log_level: str = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()