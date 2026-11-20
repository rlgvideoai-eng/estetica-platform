"""Base Channel Adapter - Interfaz común para todos los canales de mensajería."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils import get_logger

logger = get_logger(__name__)


class ChannelType(Enum):
    """Tipos de canales soportados."""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    WEB = "web"


@dataclass
class User:
    """Usuario del canal."""
    id: str                    # ID único en el canal (ej. telegram_user_id, whatsapp_phone_id)
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    channel: ChannelType = ChannelType.TELEGRAM
    
    @property
    def display_name(self) -> str:
        """Nombre para mostrar."""
        if self.first_name:
            return self.first_name
        if self.username:
            return f"@{self.username}"
        return f"User {self.id}"


@dataclass
class Message:
    """Mensaje recibido del canal."""
    id: str                    # ID único del mensaje en el canal
    user: User                 # Usuario que envió el mensaje
    channel: ChannelType       # Canal de origen
    text: Optional[str] = None         # Texto del mensaje (si es texto)
    voice: Optional[Dict] = None       # Info de nota de voz (si aplica)
    timestamp: float = 0               # Timestamp Unix
    raw_data: Optional[Dict] = None    # Datos originales del canal
    
    @property
    def is_text(self) -> bool:
        return self.text is not None and len(self.text.strip()) > 0
    
    @property
    def is_voice(self) -> bool:
        return self.voice is not None


@dataclass
class OutgoingMessage:
    """Mensaje a enviar al canal."""
    text: Optional[str] = None
    voice_bytes: Optional[bytes] = None
    caption: Optional[str] = None
    keyboard: Optional[Any] = None
    parse_mode: str = "HTML"


@dataclass
class Keyboard:
    """Teclado inline unificado."""
    buttons: List[List[Dict]]  # [[{"text": "Btn", "callback_data": "data"}], ...]


class ChannelAdapter(ABC):
    """Interfaz base para adaptadores de canales de mensajería."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger.bind(channel=self.channel_type.value)
    
    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        """Tipo de canal que implementa este adaptador."""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Inicializa el adaptador (conexiones, webhooks, etc.)."""
        pass
    
    @abstractmethod
    async def start_polling(self) -> None:
        """Inicia el polling/webhook para recibir mensajes."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Detiene el adaptador y cierra conexiones."""
        pass
    
    @abstractmethod
    async def send_message(self, user_id: str, message: OutgoingMessage) -> bool:
        """Envía un mensaje a un usuario."""
        pass
    
    @abstractmethod
    async def send_voice(self, user_id: str, audio_bytes: bytes, caption: Optional[str] = None) -> bool:
        """Envía una nota de voz a un usuario."""
        pass
    
    @abstractmethod
    async def get_user_info(self, user_id: str) -> Optional[User]:
        """Obtiene información de un usuario."""
        pass
    
    @abstractmethod
    async def set_webhook(self, url: str, secret: Optional[str] = None) -> bool:
        """Configura webhook para recibir mensajes."""
        pass
    
    @abstractmethod
    async def delete_webhook(self) -> bool:
        """Elimina webhook configurado."""
        pass
    
    @abstractmethod
    async def process_update(self, update_data: Dict[str, Any]) -> Optional[Message]:
        """Procesa una actualización cruda del canal y retorna un Message normalizado."""
        pass
    
    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verifica la firma del webhook para seguridad."""
        pass


class ChannelAdapterFactory:
    """Factory para crear instancias de adaptadores de canal."""
    
    _adapters: Dict[ChannelType, type] = {}
    
    @classmethod
    def register(cls, channel_type: ChannelType, adapter_class: type):
        """Registra una clase de adaptador."""
        cls._adapters[channel_type] = adapter_class
    
    @classmethod
    def create(cls, channel_type: ChannelType, config: Dict[str, Any]) -> ChannelAdapter:
        """Crea una instancia del adaptador."""
        if channel_type not in cls._adapters:
            raise ValueError(f"No hay adaptador registrado para {channel_type.value}")
        return cls._adapters[channel_type](config)
    
    @classmethod
    def get_available_channels(cls) -> List[ChannelType]:
        return list(cls._adapters.keys())