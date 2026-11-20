"""Notifier - Notificaciones a clientas por Telegram (recordatorios, cambios, cancelaciones)."""
import logging
from typing import Optional

from telegram import Bot

from ..config import settings
from ..utils import get_logger, format_santiago, to_santiago

logger = get_logger(__name__)

# Bot instance para notificaciones a clientas
_client_bot: Optional[Bot] = None


def _get_client_bot() -> Bot:
    global _client_bot
    if _client_bot is None:
        _client_bot = Bot(token=settings.telegram_bot_token)
    return _client_bot


async def notify_client_reminder(
    telegram_user_id: int,
    booking: dict,
) -> bool:
    """Envía recordatorio 24h a la clienta por Telegram."""
    try:
        bot = _get_client_bot()

        message = (
            f"⏰ <b>Recordatorio: Tu cita es mañana</b>\n\n"
            f"Hola <b>{booking.get('client_name', 'Clienta')}</b>,\n\n"
            f"Te recordamos tu reserva en <b>Ayudio</strong>:\n\n"
            f"📋 <b>Código:</b> {booking.get('codigo', 'N/A')}\n"
            f"💇 <b>Servicio:</b> {booking.get('service_name', 'N/A')}\n"
            f"👩‍💼 <b>Profesional:</b> {booking.get('professional_name', 'Por confirmar')}\n"
            f"📅 <b>Fecha:</b> {booking.get('date_str', 'N/A')}\n"
            f"⏰ <b>Hora:</b> {booking.get('time_str', 'N/A')}\n\n"
            f"📍 <b>Dirección:</b> Av. Providencia 1234, Providencia, Santiago\n\n"
            f"⚠️ <b>Importante:</b>\n"
            f"• Llega 10 minutos antes\n"
            f"• Cancelaciones <24h = 50% cargo\n"
            f"• No-show (no avisar) = 100% cargo\n\n"
            f"¿Necesitas cambiar tu hora? Escríbenos por este chat 👇"
        )

        await bot.send_message(
            chat_id=telegram_user_id,
            text=message,
            parse_mode="HTML",
        )

        logger.info("client_reminder_sent", telegram_user_id=telegram_user_id, booking_codigo=booking.get('codigo'))
        return True

    except Exception as e:
        logger.exception("client_reminder_error", telegram_user_id=telegram_user_id, error=str(e))
        return False


async def notify_client_booking_change(
    telegram_user_id: int,
    old_booking: dict,
    new_booking: dict,
) -> bool:
    """Notifica cambio de reserva a la clienta."""
    try:
        bot = _get_client_bot()

        message = (
            f"🔄 <b>Tu reserva ha sido reprogramada</b>\n\n"
            f"Hola <b>{new_booking.get('client_name', 'Clienta')}</b>,\n\n"
            f"Tu reserva en <b>Ayudio</b> ha sido cambiada:\n\n"
            f"❌ <b>Anterior:</b>\n"
            f"  📅 {old_booking.get('date_str', 'N/A')} a las {old_booking.get('time_str', 'N/A')}\n"
            f"  💇 {old_booking.get('service_name', 'N/A')}\n\n"
            f"✅ <b>Nueva:</b>\n"
            f"  📅 {new_booking.get('date_str', 'N/A')} a las {new_booking.get('time_str', 'N/A')}\n"
            f"  💇 {new_booking.get('service_name', 'N/A')}\n"
            f"  👩‍💼 {new_booking.get('professional_name', 'Por confirmar')}\n\n"
            f"📋 <b>Código:</b> {new_booking.get('codigo', 'N/A')}\n\n"
            f"Te hemos enviado el archivo .ics actualizado por email.\n\n"
            f"¿Todo bien? ¡Te esperamos! 💖"
        )

        await bot.send_message(
            chat_id=telegram_user_id,
            text=message,
            parse_mode="HTML",
        )

        logger.info("client_change_notified", telegram_user_id=telegram_user_id, booking_codigo=new_booking.get('codigo'))
        return True

    except Exception as e:
        logger.exception("client_change_notify_error", telegram_user_id=telegram_user_id, error=str(e))
        return False


async def notify_client_cancellation(
    telegram_user_id: int,
    booking: dict,
    cancelled_by: str = "client",
    charge_applied: bool = False,
) -> bool:
    """Notifica cancelación a la clienta."""
    try:
        bot = _get_client_bot()

        charge_text = ""
        if charge_applied:
            charge_text = (
                f"\n⚠️ <b>Cargo aplicado:</b> Al cancelar con menos de 24h, "
                f"se aplica el 50% del servicio como abono para tu próxima visita."
            )

        message = (
            f"❌ <b>Reserva Cancelada</b>\n\n"
            f"Hola,\n\n"
            f"Tu reserva en <b>Ayudio</b> ha sido cancelada:\n\n"
            f"📋 <b>Código:</b> {booking.get('codigo', 'N/A')}\n"
            f"💇 <b>Servicio:</b> {booking.get('service_name', 'N/A')}\n"
            f"📅 <b>Fecha:</b> {booking.get('date_str', 'N/A')}\n"
            f"⏰ <b>Hora:</b> {booking.get('time_str', 'N/A')}\n"
            f"{charge_text}\n\n"
            f"Cancelado por: <b>{'Tú' if cancelled_by == 'client' else 'El centro'}</b>\n\n"
            f"¿Quieres agendar una nueva hora? Escríbenos por este chat 👇"
        )

        await bot.send_message(
            chat_id=telegram_user_id,
            text=message,
            parse_mode="HTML",
        )

        logger.info("client_cancellation_notified", telegram_user_id=telegram_user_id, booking_codigo=booking.get('codigo'))
        return True

    except Exception as e:
        logger.exception("client_cancellation_notify_error", telegram_user_id=telegram_user_id, error=str(e))
        return False