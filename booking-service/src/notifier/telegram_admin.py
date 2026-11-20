"""Notifier - Notificaciones a la administradora por Telegram (desde booking-service)."""
import logging
from typing import Optional

from telegram import Bot

from ..config import settings
from ..utils import get_logger, format_santiago

logger = get_logger(__name__)

# Bot instance para notificaciones admin
_admin_bot: Optional[Bot] = None


def _get_admin_bot() -> Bot:
    global _admin_bot
    if _admin_bot is None:
        _admin_bot = Bot(token=settings.telegram_bot_token)
    return _admin_bot


async def notify_admin_handoff(
    telegram_user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    summary: str,
) -> bool:
    """Notifica a la administradora sobre una derivación a humano."""
    if not settings.admin_telegram_chat_id:
        logger.warning("admin_telegram_chat_id_not_configured")
        return False

    try:
        bot = _get_admin_bot()

        user_info = []
        if first_name:
            user_info.append(f"Nombre: {first_name}")
        if username:
            user_info.append(f"Usuario: @{username}")
        user_info.append(f"Telegram ID: {telegram_user_id}")

        message = (
            f"🔔 <b>Derivación a Humano</b>\n\n"
            f"👤 <b>Cliente:</b>\n" + "\n".join(user_info) + f"\n\n"
            f"💬 <b>Resumen:</b>\n{summary}\n\n"
            f"⏰ <i>Responde directamente a este chat para contestar al cliente.</i>"
        )

        await bot.send_message(
            chat_id=settings.admin_telegram_chat_id,
            text=message,
            parse_mode="HTML",
        )

        logger.info("admin_handoff_notified", telegram_user_id=telegram_user_id)
        return True

    except Exception as e:
        logger.exception("admin_handoff_notify_error", error=str(e))
        return False


async def notify_admin_new_booking(booking: dict) -> bool:
    """Notifica nueva reserva a la administradora."""
    if not settings.admin_telegram_chat_id:
        return False

    try:
        bot = _get_admin_bot()

        message = (
            f"🆕 <b>Nueva Reserva</b>\n\n"
            f"📋 <b>Código:</b> {booking.get('codigo', 'N/A')}\n"
            f"👤 <b>Cliente:</b> {booking.get('client_name', 'N/A')}\n"
            f"📞 <b>Teléfono:</b> {booking.get('client_phone', 'N/A')}\n"
            f"✉️ <b>Email:</b> {booking.get('client_email', 'N/A')}\n\n"
            f"💇 <b>Servicio:</b> {booking.get('service_name', 'N/A')}\n"
            f"👩‍💼 <b>Profesional:</b> {booking.get('professional_name', 'Por asignar')}\n"
            f"📅 <b>Fecha:</b> {booking.get('date_str', 'N/A')}\n"
            f"⏰ <b>Hora:</b> {booking.get('time_str', 'N/A')}\n"
            f"💰 <b>Precio:</b> ${booking.get('precio', 0):,.0f} CLP\n\n"
            f"📍 Origen: {booking.get('origen', 'telegram')}"
        )

        await bot.send_message(
            chat_id=settings.admin_telegram_chat_id,
            text=message,
            parse_mode="HTML",
        )

        logger.info("admin_new_booking_notified", booking_id=booking.get('id'))
        return True

    except Exception as e:
        logger.exception("admin_new_booking_notify_error", error=str(e))
        return False


async def notify_admin_booking_change(
    action: str,
    booking: dict,
    details: str = "",
) -> bool:
    """Notifica cambio/cancelación de reserva a la administradora."""
    if not settings.admin_telegram_chat_id:
        return False

    try:
        bot = _get_admin_bot()

        action_emoji = {
            "rescheduled": "🔄",
            "cancelled": "❌",
            "confirmed": "✅",
        }.get(action, "📝")

        message = (
            f"{action_emoji} <b>Reserva {action.capitalize()}</b>\n\n"
            f"📋 <b>Código:</b> {booking.get('codigo', 'N/A')}\n"
            f"👤 <b>Cliente:</b> {booking.get('client_name', 'N/A')}\n"
            f"💇 <b>Servicio:</b> {booking.get('service_name', 'N/A')}\n"
            f"📅 <b>Fecha:</b> {booking.get('date_str', 'N/A')}\n"
            f"⏰ <b>Hora:</b> {booking.get('time_str', 'N/A')}\n"
        )

        if details:
            message += f"\n📝 <b>Detalles:</b> {details}"

        await bot.send_message(
            chat_id=settings.admin_telegram_chat_id,
            text=message,
            parse_mode="HTML",
        )

        logger.info("admin_booking_change_notified", action=action, booking_id=booking.get('id'))
        return True

    except Exception as e:
        logger.exception("admin_booking_change_notify_error", error=str(e))
        return False


async def notify_admin_reminder_sent(booking: dict) -> bool:
    """Notifica que se envió recordatorio 24h."""
    if not settings.admin_telegram_chat_id:
        return False

    try:
        bot = _get_admin_bot()

        message = (
            f"⏰ <b>Recordatorio Enviado</b>\n\n"
            f"📋 <b>Código:</b> {booking.get('codigo', 'N/A')}\n"
            f"👤 <b>Cliente:</b> {booking.get('client_name', 'N/A')}\n"
            f"💇 <b>Servicio:</b> {booking.get('service_name', 'N/A')}\n"
            f"📅 <b>Mañana a las:</b> {booking.get('time_str', 'N/A')}\n"
            f"📧 Email y Telegram enviados."
        )

        await bot.send_message(
            chat_id=settings.admin_telegram_chat_id,
            text=message,
            parse_mode="HTML",
        )

        return True

    except Exception as e:
        logger.exception("admin_reminder_notify_error", error=str(e))
        return False