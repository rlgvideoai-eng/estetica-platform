"""Channels package - Channel adapters for different messaging platforms."""
from .base import ChannelAdapter, Message, User, ChannelType
from .telegram_adapter import TelegramAdapter
from .whatsapp_adapter import WhatsAppAdapter
from .factory import get_channel_adapter

__all__ = [
    "ChannelAdapter",
    "Message",
    "User",
    "ChannelType",
    "TelegramAdapter",
    "WhatsAppAdapter",
    "get_channel_adapter",
]