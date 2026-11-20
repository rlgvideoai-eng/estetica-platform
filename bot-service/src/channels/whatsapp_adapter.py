"""WhatsApp Adapter - Adaptador para WhatsApp Business API (Meta Cloud API)."""
import hmac
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from .base import ChannelAdapter, ChannelType, User, Message, OutgoingMessage, Keyboard
from ..config import settings
from ..utils import get_logger

logger = get_logger(__name__)


class WhatsAppAdapter(ChannelAdapter):
    """Adaptador para WhatsApp Business API (Meta Cloud API)."""
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WHATSAPP
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.phone_number_id = config.get("whatsapp_phone_number_id") or settings.whatsapp_phone_number_id
        self.access_token = config.get("whatsapp_access_token") or settings.whatsapp_access_token
        self.webhook_verify_token = config.get("whatsapp_webhook_verify_token") or settings.whatsapp_webhook_verify_token
        self.business_account_id = config.get("whatsapp_business_account_id") or settings.whatsapp_business_account_id
        
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        
        # Mapeo de estados de mensajes
        self._message_status_map = {
            "sent": "sent",
            "delivered": "delivered",
            "read": "read",
            "failed": "failed",
        }
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WHATSAPP
    
    async def initialize(self) -> None:
        """Inicializa el cliente HTTP para WhatsApp API."""
        if self._initialized:
            return
        
        if not self.access_token or not self.phone_number_id:
            logger.warning("whatsapp_not_configured", 
                          has_token=bool(self.access_token), 
                          has_phone_id=bool(self.phone_number_id))
            return
        
        self._client = httpx.AsyncClient(
            base_url="https://graph.facebook.com/v19.0",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        
        self._initialized = True
        logger.info("whatsapp_adapter_initialized")
    
    async def start_polling(self) -> None:
        """WhatsApp usa webhooks, no polling. Este método configura el webhook."""
        logger.info("whatsapp_adapter_ready_webhook_mode")
        # En WhatsApp no hay polling, se usa webhook
        pass
    
    async def stop(self) -> None:
        """Cierra conexiones."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("whatsapp_adapter_stopped")
    
    async def send_message(self, user_id: str, message: Any) -> bool:
        """Envía un mensaje de texto a un usuario de WhatsApp."""
        if not self._client:
            logger.error("whatsapp_client_not_initialized")
            return False
        
        try:
            # Formatear número: quitar + y espacios
            to_number = user_id.replace("+", "").replace(" ", "").replace("-", "")
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message.text or "",
                },
            }
            
            # Agregar botones si hay keyboard
            if message.keyboard:
                buttons = []
                for row in message.keyboard.buttons:
                    for btn in row:
                        buttons.append({
                            "type": "reply",
                            "reply": {
                                "id": btn.get("callback_data", "btn"),
                                "title": btn.get("text", "")[:20],  # WhatsApp límite 20 chars
                            }
                        })
                
                if buttons:
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": to_number,
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {"text": message.text or ""},
                            "action": {"buttons": buttons[:3]},  # WhatsApp máx 3 botones
                        },
                    }
            
            response = await self._client.post(
                f"/{self.phone_number_id}/messages",
                json=payload,
            )
            
            if response.status_code == 200:
                logger.info("whatsapp_message_sent", to=user_id)
                return True
            else:
                logger.error("whatsapp_send_failed", status=response.status_code, error=response.text)
                return False
                
        except Exception as e:
            logger.exception("whatsapp_send_error", error=str(e), user_id=user_id)
            return False
    
    async def send_voice(self, user_id: str, audio_bytes: bytes, caption: Optional[str] = None) -> bool:
        """Envía nota de voz a WhatsApp (requiere subir media primero)."""
        try:
            if not self._client:
                return False
            
            # 1. Subir archivo de audio
            import io
            audio_file = io.BytesIO(audio_bytes)
            
            files = {
                "file": ("voice.ogg", audio_bytes, "audio/ogg"),
                "messaging_product": (None, "whatsapp"),
                "type": (None, "audio"),
            }
            
            upload_response = await self._client.post(
                f"/{self.phone_number_id}/media",
                files=files,
            )
            
            if upload_response.status_code != 200:
                logger.error("whatsapp_media_upload_failed", status=upload_response.status_code)
                return False
            
            media_id = upload_response.json().get("id")
            if not media_id:
                logger.error("whatsapp_no_media_id")
                return False
            
            # 2. Enviar mensaje de audio
            to_number = user_id.replace("+", "").replace(" ", "").replace("-", "")
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "audio",
                "audio": {
                    "id": media_id,
                },
            }
            
            response = await self._client.post(
                f"/{self.phone_number_id}/messages",
                json=payload,
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.exception("whatsapp_send_voice_error", error=str(e))
            return False
    
    async def get_user_info(self, user_id: str) -> Optional[Any]:
        """Obtiene info del usuario (en WhatsApp es básico)."""
        from ..base import User
        return User(
            id=user_id,
            channel=self.channel_type,
        )
    
    async def set_webhook(self, url: str, secret: Optional[str] = None) -> bool:
        """Configura webhook en Meta."""
        try:
            if not self._client:
                return False
            
            verify_token = self.webhook_verify_token or "ayudio_webhook_verify"
            
            payload = {
                "url": url,
                "verify_token": verify_token,
                "fields": ["messages", "message_deliveries", "message_reads", "message_reactions"],
            }
            
            response = await self._client.post(
                f"/{self.phone_number_id}/webhooks",
                json=payload,
            )
            
            if response.status_code == 200:
                logger.info("whatsapp_webhook_set", url=url)
                return True
            else:
                logger.error("whatsapp_webhook_failed", status=response.status_code, error=response.text)
                return False
                
        except Exception as e:
            logger.exception("whatsapp_webhook_error", error=str(e))
            return False
    
    async def delete_webhook(self) -> bool:
        """Elimina webhook."""
        # Meta no permite eliminar webhook via API fácilmente
        # Se hace desde Meta Developer Console
        logger.warning("whatsapp_delete_webhook_not_supported")
        return False
    
    async def process_update(self, update_data: Dict[str, Any]) -> Optional[Any]:
        """Procesa webhook de WhatsApp y retorna Message normalizado."""
        try:
            entry = update_data.get("entry", [])
            if not entry:
                return None
            
            changes = entry[0].get("changes", [])
            if not changes:
                return None
            
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None
            
            msg = messages[0]
            from_number = msg.get("from", "")
            
            # Normalizar usuario
            user = User(
                id=from_number,
                channel=ChannelType.WHATSAPP,
            )
            
            # Procesar según tipo de mensaje
            msg_type = msg.get("type", "text")
            
            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")
                return Message(
                    id=msg.get("id", ""),
                    user=User(id=from_number, channel=ChannelType.WHATSAPP),
                    channel=ChannelType.WHATSAPP,
                    text=text,
                    timestamp=int(msg.get("timestamp", 0)),
                    raw_data=msg,
                )
            elif msg_type == "audio":
                # Nota de voz en WhatsApp
                audio = msg.get("audio", {})
                return Message(
                    id=msg.get("id", ""),
                    user=User(id=from_number, channel=ChannelType.WHATSAPP),
                    channel=ChannelType.WHATSAPP,
                    voice={
                        "id": audio.get("id"),
                        "mime_type": audio.get("mime_type"),
                        "sha256": audio.get("sha256"),
                    },
                    timestamp=int(msg.get("timestamp", 0)),
                    raw_data=msg,
                )
            elif msg_type == "interactive":
                # Respuesta a botón interactivo
                interactive = msg.get("interactive", {})
                button_reply = interactive.get("button_reply", {})
                return Message(
                    id=msg.get("id", ""),
                    user=User(id=from_number, channel=ChannelType.WHATSAPP),
                    channel=ChannelType.WHATSAPP,
                    text=button_reply.get("id", ""),  # ID del botón presionado
                    raw_data=msg,
                )
            
            return None
            
        except Exception as e:
            logger.exception("whatsapp_process_update_error", error=str(e))
            return None
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verifica firma X-Hub-Signature-256 de Meta."""
        if not self.webhook_verify_token:
            return True
        
        expected = hmac.new(
            self.webhook_verify_token.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Meta envía: sha256=<hash>
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        return hmac.compare_digest(expected, signature)
    
    async def send_message(self, user_id: str, message: Any) -> bool:
        return await self.send_message(user_id, message)
    
    async def send_voice(self, user_id: str, audio_bytes: bytes, caption: Optional[str] = None) -> bool:
        return await self.send_voice(user_id, audio_bytes, caption)
    
    async def get_user_info(self, user_id: str) -> Any:
        return await self.get_user_info(user_id)
    
    async def set_webhook(self, url: str, secret: Optional[str] = None) -> bool:
        return await self.set_webhook(url, secret)
    
    async def delete_webhook(self) -> bool:
        return await self.delete_webhook()
    
    async def process_update(self, update_data: Dict[str, Any]) -> Any:
        return await self.process_update(update_data)
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        return self.verify_webhook_signature(payload, signature)