"""Factory para obtener adaptadores de canal."""
from typing import Dict, Any, Optional

from .base import ChannelAdapter, ChannelType, ChannelAdapterFactory
from .telegram_adapter import TelegramAdapter
from .whatsapp_adapter import WhatsAppAdapter
from ..config import settings
from ..utils import get_logger

logger = get_logger(__name__)

# Registrar adaptadores disponibles
ChannelAdapterFactory.register(ChannelType.TELEGRAM, TelegramAdapter)
ChannelAdapterFactory.register(ChannelType.WHATSAPP, WhatsAppAdapter)


def get_channel_adapter(
    channel: ChannelType,
    config: Optional[Dict[str, Any]] = None,
) -> ChannelAdapter:
    """Obtiene una instancia del adaptador de canal configurado."""
    if config is None:
        config = {}
    
    # Configuración base desde settings
    base_config = {
        "telegram_bot_token": settings.telegram_bot_token,
        "telegram_webhook_secret": settings.telegram_webhook_secret,
        "admin_telegram_chat_id": settings.admin_telegram_chat_id,
        "whatsapp_phone_number_id": getattr(settings, "whatsapp_phone_number_id", None),
        "whatsapp_access_token": getattr(settings, "whatsapp_access_token", None),
        "whatsapp_webhook_verify_token": getattr(settings, "whatsapp_webhook_verify_token", None),
        "whatsapp_business_account_id": getattr(settings, "whatsapp_business_account_id", None),
    }
    
    # Merge con config personalizada
    final_config = {**base_config, **config}
    
    try:
        return ChannelAdapterFactory.create(channel, final_config)
    except ValueError as e:
        logger.error("channel_adapter_not_found", channel=channel.value)
        raise


async def initialize_all_channels(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Inicializa todos los canales configurados."""
    adapters = {}
    
    # Siempre inicializar Telegram (canal principal)
    if settings.telegram_bot_token:
        try:
            telegram = get_channel_adapter(ChannelType.TELEGRAM)
            await telegram.initialize()
            await telegram.start_polling()
            adapters["telegram"] = telegram
            logger.info("telegram_channel_initialized")
        except Exception as e:
            logger.exception("telegram_init_failed", error=str(e))
    
    # Inicializar WhatsApp si está configurado
    if getattr(settings, "whatsapp_access_token", None) and getattr(settings, "whatsapp_phone_number_id", None):
        try:
            whatsapp = get_channel_adapter(ChannelType.WHATSAPP)
            await whatsapp.initialize()
            adapters["whatsapp"] = whatsapp
            logger.info("whatsapp_channel_initialized")
        except Exception as e:
            logger.exception("whatsapp_init_failed", error=str(e))
    
    return adapters


async def shutdown_all_channels(adapters: Dict[str, Any]) -> None:
    """Detiene todos los canales."""
    for name, adapter in adapters.items():
        try:
            await adapter.stop()
            logger.info(f"{name}_channel_stopped")
        except Exception as e:
            logger.exception(f"{name}_channel_stop_error", error=str(e))