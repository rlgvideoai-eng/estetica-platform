"""Configuración centralizada con Pydantic Settings."""
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
    # Telegram
    # -------------------------------------------
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = Field(..., validation_alias="TELEGRAM_WEBHOOK_SECRET")
    admin_telegram_chat_id: int = Field(..., validation_alias="ADMIN_TELEGRAM_CHAT_ID")

    # -------------------------------------------
    # LLM (Nemotron Nano Omni)
    # -------------------------------------------
    llm_provider: Literal["nemotron", "openai", "mock"] = Field(
        default="nemotron", validation_alias="LLM_PROVIDER"
    )
    llm_api_key: str = Field(..., validation_alias="LLM_API_KEY")
    llm_model: str = Field(default="nemotron-nano-omni", validation_alias="LLM_MODEL")
    llm_base_url: Optional[str] = Field(default=None, validation_alias="LLM_BASE_URL")

    # -------------------------------------------
    # RAG (Databricks / Mock)
    # -------------------------------------------
    databricks_rag_url: str = Field(default="http://rag-mock:8000", validation_alias="DATABRICKS_RAG_URL")
    databricks_token: Optional[str] = Field(default=None, validation_alias="DATABRICKS_TOKEN")

    # -------------------------------------------
    # Booking Service
    # -------------------------------------------
    booking_service_url: str = Field(default="http://booking-service:8000", validation_alias="BOOKING_SERVICE_URL")
    internal_api_key: str = Field(default="dev-internal-key-change-in-prod", validation_alias="INTERNAL_API_KEY")

    # -------------------------------------------
    # Email / Notificaciones
    # -------------------------------------------
    admin_email: str = Field(..., validation_alias="ADMIN_EMAIL")
    email_from: str = Field(default="noreply@ayudio.cl", validation_alias="EMAIL_FROM")
    email_provider_key: Optional[str] = Field(default=None, validation_alias="EMAIL_PROVIDER_KEY")

    # -------------------------------------------
    # Configuración General
    # -------------------------------------------
    timezone: str = Field(default="America/Santiago", validation_alias="TIMEZONE")
    cancel_min_hours: int = Field(default=24, validation_alias="CANCEL_MIN_HOURS")

    # -------------------------------------------
    # Voz (Fase 5)
    # -------------------------------------------
    stt_provider: Literal["mock", "faster-whisper", "huggingface"] = Field(
        default="mock", validation_alias="STT_PROVIDER"
    )
    tts_provider: Literal["mock", "piper", "huggingface"] = Field(
        default="mock", validation_alias="TTS_PROVIDER"
    )

    # -------------------------------------------
    # WhatsApp (Fase 6)
    # -------------------------------------------
    whatsapp_phone_number_id: Optional[str] = Field(default=None, validation_alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_access_token: Optional[str] = Field(default=None, validation_alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_webhook_verify_token: Optional[str] = Field(default=None, validation_alias="WHATSAPP_WEBHOOK_VERIFY_TOKEN")
    whatsapp_business_account_id: Optional[str] = Field(default=None, validation_alias="WHATSAPP_BUSINESS_ACCOUNT_ID")

    # -------------------------------------------
    # Logging
    # -------------------------------------------
    log_level: str = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()