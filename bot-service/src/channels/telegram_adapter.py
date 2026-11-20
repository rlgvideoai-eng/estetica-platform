"""Telegram Adapter - Adaptador para python-telegram-bot."""
import logging
from typing import Any, Dict, List, Optional

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from .base import ChannelAdapter, ChannelType, User, Message, OutgoingMessage, Keyboard
from ..config import settings
from ..utils import get_logger, set_correlation_id, clear_correlation_id
from ..bot.handler import (
    cmd_start, cmd_ayuda, cmd_voz, cmd_mi_reserva, cmd_cancelar, cmd_reprogramar,
    handle_callback_query, handle_text_message, handle_voice_message, error_handler,
    setup_bot as setup_bot_original,
)

logger = get_logger(__name__)


class TelegramAdapter(ChannelAdapter):
    """Adaptador para Telegram usando python-telegram-bot."""
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.TELEGRAM
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = config.get("telegram_bot_token") or settings.telegram_bot_token
        self.webhook_secret = config.get("telegram_webhook_secret") or settings.telegram_webhook_secret
        self.admin_chat_id = config.get("admin_telegram_chat_id") or settings.admin_telegram_chat_id
        self.bot_token = self.token
        
        self._application: Optional[Any] = None
        self._bot: Optional[Bot] = None
        self._initialized = False
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.TELEGRAM
    
    async def initialize(self) -> None:
        """Inicializa la aplicación de Telegram."""
        if self._initialized:
            return
        
        builder = ApplicationBuilder().token(self.bot_token)
        
        if self.webhook_secret:
            from ..config import settings
            builder = builder.webhook_secret_token(settings.telegram_webhook_secret)
        
        self._application = builder.build()
        self._bot = self._application.bot
        
        # Registrar handlers reutilizando los existentes
        from ..bot.handler import (
            cmd_start, cmd_ayuda, cmd_voz, cmd_mi_reserva, cmd_cancelar, cmd_reprogramar,
            handle_callback_query, handle_text_message, handle_voice_message, error_handler
        )
        
        self._application.add_handler(CommandHandler("start", cmd_start))
        self._application.add_handler(CommandHandler("ayuda", cmd_ayuda))
        self._application.add_handler(CommandHandler("voz", cmd_voz))
        self._application.add_handler(CommandHandler("mi_reserva", cmd_mi_reserva))
        self._application.add_handler(CommandHandler("cancelar", cmd_cancelar))
        self._application.add_handler(CommandHandler("reprogramar", cmd_reprogramar))
        
        self._application.add_handler(CallbackQueryHandler(self._handle_callback_query_wrapper))
        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message_wrapper))
        self._application.add_handler(MessageHandler(filters.VOICE, self._handle_voice_message_wrapper))
        self._application.add_error_handler(error_handler)
        
        self._initialized = True
        logger.info("telegram_adapter_initialized")
    
    async def _handle_callback_query_wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapper para manejar callback queries con ChannelAdapter."""
        from ..bot.handler import handle_callback_query
        await handle_callback_query(update, context)
    
    async def _handle_text_message_wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapper para mensajes de texto."""
        from ..bot.handler import handle_text_message
        await handle_text_message(update, context)
    
    async def _handle_voice_message_wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapper para mensajes de voz."""
        from ..bot.handler import handle_voice_message
        await handle_voice_message(update, context)
    
    async def start_polling(self) -> None:
        """Inicia polling de Telegram."""
        if not self._initialized:
            await self.initialize()
        
        await self._application.initialize()
        await self._application.start()
        await self._application.updater.start_polling(
            allowed_updates=["message", "callback_query", "voice"],
            drop_pending_updates=True,
        )
        logger.info("telegram_polling_started")
    
    async def stop(self) -> None:
        """Detiene el bot de Telegram."""
        if self._application:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
            logger.info("telegram_adapter_stopped")
    
    async def send_message(self, user_id: str, message: Any) -> bool:
        """Envía un mensaje de texto a un usuario."""
        try:
            if not self._bot:
                logger.error("bot_not_initialized")
                return False
            
            keyboard = None
            if message.keyboard:
                # Convertir Keyboard unificado a InlineKeyboardMarkup
                inline_keyboard = []
                for row in message.keyboard.buttons:
                    row_buttons = []
                    for btn in row:
                        row_buttons.append(InlineKeyboardButton(
                            text=btn.get("text", ""),
                            callback_data=btn.get("callback_data", "")
                        ))
                    inline_keyboard.append(row_buttons)
                keyboard = InlineKeyboardMarkup(inline_keyboard)
            
            await self._bot.send_message(
                chat_id=int(user_id),
                text=message.text or "",
                parse_mode=message.parse_mode or "HTML",
                reply_markup=keyboard,
            )
            return True
        except Exception as e:
            logger.exception("telegram_send_message_error", error=str(e), user_id=user_id)
            return False
    
    async def send_voice(self, user_id: str, audio_bytes: bytes, caption: Optional[str] = None) -> bool:
        """Envía una nota de voz a un usuario."""
        try:
            if not self._bot:
                return False
            
            import io
            voice_file = io.BytesIO(audio_bytes)
            voice_file.name = "voice.ogg"
            
            await self._bot.send_voice(
                chat_id=int(user_id),
                voice=voice_file,
                caption=caption,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.exception("telegram_send_voice_error", error=str(e), user_id=user_id)
            return False
    
    async def get_user_info(self, user_id: str) -> Optional[Any]:
        """Obtiene información del usuario (limitado en Telegram Bot API)."""
        # En Telegram Bot API no hay método directo para obtener info de usuario
        # Retornamos info básica
        from ..base import User
        return User(
            id=user_id,
            channel=self.channel_type,
        )
    
    async def set_webhook(self, url: str, secret: Optional[str] = None) -> bool:
        """Configura webhook para recibir mensajes."""
        try:
            if not self._bot:
                return False
            
            secret_token = secret or settings.telegram_webhook_secret
            await self._bot.set_webhook(
                url=url,
                secret_token=secret_token,
                allowed_updates=["message", "callback_query", "voice"],
                drop_pending_updates=True,
            )
            logger.info("telegram_webhook_set", url=url)
            return True
        except Exception as e:
            logger.exception("telegram_set_webhook_error", error=str(e))
            return False
    
    async def delete_webhook(self) -> bool:
        """Elimina webhook configurado."""
        try:
            if self._bot:
                await self._bot.delete_webhook(drop_pending_updates=True)
                logger.info("telegram_webhook_deleted")
                return True
        except Exception as e:
            logger.exception("telegram_delete_webhook_error", error=str(e))
        return False
    
    async def process_update(self, update_data: Dict[str, Any]) -> Optional[Any]:
        """Procesa una actualización cruda de Telegram y retorna Message normalizado."""
        if not self._application:
            return None
        
        # Crear Update object
        update = Update.de_json(update_data, self._application.bot)
        
        # Normalizar a Message unificado
        if update.message:
            user = update.message.from_user
            return self._normalize_message(update.message, user)
        elif update.callback_query:
            user = update.callback_query.from_user
            # Para callback queries, crear mensaje sintético
            return Message(
                id=str(update.callback_query.id),
                user=User(
                    id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=user.language_code,
                ),
                channel=ChannelType.TELEGRAM,
                text=update.callback_query.data,
                raw_data=update_data,
            )
        return None
    
    def _normalize_message(self, tg_message, user) -> Any:
        """Normaliza mensaje de Telegram a Message unificado."""
        from ..base import Message, User, ChannelType
        
        text = tg_message.text
        voice = None
        if tg_message.voice:
            voice = {
                "file_id": tg_message.voice.file_id,
                "duration": tg_message.voice.duration,
                "file_size": tg_message.voice.file_size,
            }
        
        return Message(
            id=str(tg_message.message_id),
            user=User(
                id=str(user.id),
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                channel=ChannelType.TELEGRAM,
            ),
            channel=ChannelType.TELEGRAM,
            text=text,
            voice=voice,
            timestamp=tg_message.date.timestamp() if tg_message.date else 0,
            raw_data=tg_message.to_dict(),
        )
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verifica la firma del webhook de Telegram."""
        if not self.webhook_secret:
            return True
        import hmac
        import hashlib
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    async def send_message(self, user_id: str, message: Any) -> bool:
        return await self.send_message(user_id, message)
    
    async def send_voice(self, user_id: str, audio_bytes: bytes, caption: Optional[str] = None) -> bool:
        return await self.send_voice(user_id, audio_bytes, caption)
    
    async def start_polling(self) -> None:
        await self.start_polling()
    
    async def stop(self) -> None:
        await self.stop()
    
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