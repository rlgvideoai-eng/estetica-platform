"""Telegram Bot Handler - Configuración y dispatch de actualizaciones."""
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..config import settings
from ..utils import get_logger, get_correlation_id, set_correlation_id, clear_correlation_id
from .keyboards import MAIN_MENU_KEYBOARD, SERVICE_KEYBOARD, PROFESSIONAL_KEYBOARD
from ..agent.core import run_agent_turn

logger = get_logger(__name__)

# Aplicación global de python-telegram-bot
bot_application: Optional[Application] = None


async def setup_bot() -> None:
    """Inicializa la aplicación del bot."""
    global bot_application

    if bot_application is not None:
        return

    builder = ApplicationBuilder().token(settings.telegram_bot_token)

    # Configurar webhook secret si está en modo webhook
    if settings.telegram_webhook_secret:
        builder = builder.webhook_secret_token(settings.telegram_webhook_secret)

    bot_application = builder.build()

    # Registrar handlers
    _register_handlers(bot_application)

    logger.info("bot_application_built")


def _register_handlers(app: Application) -> None:
    """Registra todos los handlers de comandos y mensajes."""

    # Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("voz", cmd_voz))
    app.add_handler(CommandHandler("mi_reserva", cmd_mi_reserva))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(CommandHandler("reprogramar", cmd_reprogramar))

    # Callback queries (botones inline)
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Mensajes de texto
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Mensajes de voz (fase 5)
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    # Error handler global
    app.add_error_handler(error_handler)

    logger.info("handlers_registered")


# ============================================================
# HANDLERS DE COMANDOS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja /start con parámetro opcional de origen."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")

    user = update.effective_user
    args = context.args

    # Extraer origen (p.ej. ?start=landing)
    origen = args[0] if args else "directo"

    logger.info(
        "cmd_start",
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        origen=origen,
    )

    # Guardar origen en user_data para analytics
    context.user_data["origen"] = origen
    context.user_data["telegram_user_id"] = user.id

    # Mensaje de bienvenida
    welcome_text = (
        f"¡Hola {user.first_name}! 👋\n\n"
        f"Bienvenid@ a <b>Ayudio</b>, tu centro de estética de confianza. "
        f"Estoy aquí para ayudarte a informarte y agendar tu hora 24/7, sin esperas.\n\n"
        f"¿En qué puedo ayudarte hoy?"
    )

    await update.message.reply_html(
        welcome_text,
        reply_markup=MAIN_MENU_KEYBOARD,
    )


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja /ayuda."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")

    help_text = (
        "🤖 <b>Ayuda - Ayudio Bot</b>\n\n"
        "Puedo ayudarte con:\n"
        "• 📋 Ver servicios y precios\n"
        "• 📅 Agendar, reprogramar o cancelar tu hora\n"
        "• 📍 Ver ubicación y horarios\n"
        • Responder tus dudas sobre tratamientos\n\n"
        "<b>Comandos disponibles:</b>\n"
        "/start - Menú principal\n"
        "/ayuda - Esta ayuda\n"
        "/mi_reserva - Ver tu reserva activa\n"
        "/cancelar - Cancelar tu reserva\n"
        "/voz on|off - Activar/desactivar respuestas de voz\n\n"
        "También puedes usar los botones del menú 👇"
    )

    await update.message.reply_html(help_text, reply_markup=MAIN_MENU_KEYBOARD)


async def cmd_voz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja /voz on|off para activar/desactivar respuestas de audio."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")

    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        await update.message.reply_html(
            "Uso: <code>/voz on</code> para activar audio\n"
            "<code>/voz off</code> para desactivar"
        )
        return

    enabled = args[0].lower() == "on"
    context.user_data["voice_enabled"] = enabled

    status = "activado 🔊" if enabled else "desactivado 🔇"
    await update.message.reply_html(f"Respuestas de voz {status}")


async def cmd_mi_reserva(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja /mi_reserva - delega al agente."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")
    await _delegate_to_agent(update, context, "quiero ver mi reserva")


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja /cancelar - delega al agente."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")
    await _delegate_to_agent(update, context, "quiero cancelar mi reserva")


async def cmd_reprogramar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja /reprogramar - inicia flujo de reprogramación."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")
    
    # Obtener reserva activa del usuario
    from ..booking.client import get_booking
    user_id = update.effective_user.id
    booking = await get_booking(telegram_user_id=user_id)
    
    if not booking or not booking.get("bookings"):
        await update.message.reply_html(
            "📭 <b>No tienes reservas activas.</b>\n\n"
            "Usa /start para agendar una nueva hora."
        )
        return

    b = booking["bookings"][0]
    # Solo mostrar reservas pending o confirmed
    if b.get("estado") not in ["pending", "confirmed"]:
        await update.message.reply_html(
            "📭 <b>No tienes reservas activas para reprogramar.</b>\n\n"
            "Usa /start para agendar una nueva hora."
        )
        return

    await update.message.reply_html(
        f"🔄 <b>Reprogramar Reserva</b>\n\n"
        f"📋 <b>Código:</b> {b.get('codigo', 'N/A')}\n"
        f"💇 <b>Servicio:</b> {b.get('service_name', 'N/A')}\n"
        f"📅 <b>Fecha actual:</b> {b.get('date_str', 'N/A')}\n"
        f"⏰ <b>Hora actual:</b> {b.get('time_str', 'N/A')}\n\n"
        f"¿A qué fecha y hora te gustaría cambiarla?\n\n"
        f"Escribe: <code>DD/MM/YYYY HH:MM</code>\n"
        f"Ejemplo: <code>25/11/2024 15:30</code>\n\n"
        f"O usa los botones para elegir día:",
        parse_mode="HTML",
        reply_markup=RESCHEDULE_DATE_KEYBOARD,
    )
    context.user_data["awaiting_reschedule_datetime"] = True
    context.user_data["reschedule_booking_id"] = b.get("id")


# ============================================================
# CALLBACK QUERIES (BOTONES INLINE)
# ============================================================

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja todos los callback queries de botones inline."""
    query = update.callback_query
    await query.answer()

    set_correlation_id(f"tg-{query.from_user.id}-{query.id}")
    data = query.data

    logger.info("callback_query", user_id=query.from_user.id, data=data)

    # Formato: action:param1:param2...
    parts = data.split(":")
    action = parts[0]

    try:
        if action == "menu":
            await _handle_menu_action(query, parts[1:], context)

        elif action == "service":
            await _handle_service_action(query, parts[1:], context)

        elif action == "prof":
            await _handle_professional_action(query, parts[1:], context)

        elif action == "slot":
            await _handle_slot_action(query, parts[1:], context)

        elif action == "confirm":
            await _handle_confirm_action(query, parts[1:], context)

        elif action == "cancel_booking":
            await _handle_cancel_booking_action(query, parts[1:], context)

        elif action == "reschedule":
            await _handle_reschedule_action(query, parts[1:], context)

        elif action == "confirm_reschedule":
            await _handle_confirm_reschedule_action(query, parts[1:], context)

        else:
            logger.warning("unknown_callback_action", action=action)
            await query.edit_message_text("❌ Acción no reconocida. Intenta de nuevo.")

    except Exception as e:
        logger.exception("callback_query_error", data=data, error=str(e))
        await query.edit_message_text(
            "❌ Ocurrió un error. Por favor intenta de nuevo o escribe /start para volver al menú."
        )


async def _handle_menu_action(query, params, context):
    """Maneja acciones del menú principal."""
    action = params[0] if params else ""

    if action == "services":
        text = "📋 <b>Nuestros Servicios</b>\n\nElige una categoría para ver detalles y precios:"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=SERVICE_KEYBOARD)

    elif action == "book":
        text = "📅 <b>Agendar Hora</b>\n\nPrimero, elige el servicio que deseas:"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=SERVICE_KEYBOARD)

    elif action == "my_booking":
        # Mostrar reserva activa con opciones
        from ..booking.client import get_booking
        user_id = query.from_user.id
        booking = await get_booking(telegram_user_id=user_id)
        
        if not booking or not booking.get("bookings"):
            await query.edit_message_text(
                "📭 <b>No tienes reservas activas.</b>\n\n"
                "Usa el botón \"Agendar hora\" para crear una.",
                parse_mode="HTML",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
            return

        b = booking["bookings"][0]
        # Solo mostrar reservas pending o confirmed
        if b.get("estado") not in ["pending", "confirmed"]:
            await query.edit_message_text(
                "📭 <b>No tienes reservas activas.</b>\n\n"
                "Usa el botón \"Agendar hora\" para crear una.",
                parse_mode="HTML",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
            return

        # Construir teclado con opciones
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Reprogramar", callback_data=f"reschedule:{b.get('id')}"),
                InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel_booking:{b.get('id')}:confirm"),
            ],
            [
                InlineKeyboardButton("« Volver al menú", callback_data="menu:main"),
            ],
        ])

        estado_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "cancelled": "❌",
            "completed": "✅",
            "no_show": "⚠️",
        }.get(b.get('estado'), "❓")

        await query.edit_message_text(
            f"📋 <b>Tu Reserva Activa</b> {estado_emoji}\n\n"
            f"📋 <b>Código:</b> {b.get('codigo', 'N/A')}\n"
            f"💇 <b>Servicio:</b> {b.get('service_name', 'N/A')}\n"
            f"👩‍💼 <b>Profesional:</b> {b.get('professional_name', 'Por confirmar')}\n"
            f"📅 <b>Fecha:</b> {b.get('date_str', 'N/A')}\n"
            f"⏰ <b>Hora:</b> {b.get('time_str', 'N/A')}\n"
            f"💰 <b>Precio:</b> ${b.get('precio', 0):,.0f} CLP\n"
            f"📍 <b>Estado:</b> {b.get('estado', 'N/A')}\n\n"
            f"¿Qué deseas hacer?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    elif action == "human":
        # Derivación a humano
        await query.edit_message_text(
            "👩‍💼 <b>Derivación a una persona</b>\n\n"
            "Te voy a conectar con nuestra administradora. "
            "Por favor describe brevemente tu consulta y ella te responderá a la brevedad.\n\n"
            "¿Qué necesitas?",
            parse_mode="HTML",
        )
        # Marcar en context para que el siguiente mensaje de texto se envíe como handoff
        context.user_data["awaiting_handoff"] = True

    elif action == "location":
        await query.edit_message_text(
            "📍 <b>Ubicación y Horarios</b>\n\n"
            "📍 Av. Providencia 1234, Providencia, Santiago\n"
            "🕐 Lunes a Viernes: 09:00 - 19:00\n"
            "🕐 Sábado: 09:00 - 14:00\n"
            "📞 +56 2 2233 4455\n"
            "✉️ hola@ayudio.cl\n\n"
            "<a href='https://maps.app.goo.gl/ejemplo'>Ver en Google Maps</a>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    else:
        await query.edit_message_text("Opción no reconocida.")


async def _handle_service_action(query, params, context):
    """Maneja selección de servicio."""
    if not params:
        return

    service_id = params[0]
    context.user_data["selected_service_id"] = service_id

    # Preguntar por profesional (si aplica) o pasar directo a disponibilidad
    text = (
        f"✅ Servicio seleccionado.\n\n"
        f"¿Tenés preferencia por alguna profesional?\n"
        f"Si no, te mostraré disponibilidad con cualquiera disponible."
    )

    # Obtener profesionales que hacen este servicio (mock por ahora)
    from ..booking.client import get_professionals_for_service
    professionals = await get_professionals_for_service(service_id)

    if professionals:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=PROFESSIONAL_KEYBOARD(professionals))
    else:
        # Sin profesionales específicos, ir directo a disponibilidad
        context.user_data["selected_professional_id"] = None
        await _show_availability(query, context, service_id, None)


async def _handle_professional_action(query, params, context):
    """Maneja selección de profesional."""
    if not params:
        return

    professional_id = params[0]
    context.user_data["selected_professional_id"] = professional_id
    service_id = context.user_data.get("selected_service_id")

    await _show_availability(query, context, service_id, professional_id)


async def _show_availability(query, context, service_id, professional_id):
    """Muestra slots disponibles delegando al agente/booking."""
    from ..booking.client import check_availability
    from datetime import datetime, timedelta

    # Rango: próximos 14 días
    from_date = datetime.now()
    to_date = from_date + timedelta(days=14)

    try:
        slots = await check_availability(service_id, from_date, to_date, professional_id)

        if not slots:
            await query.edit_message_text(
                "😔 No hay disponibilidad para los próximos 14 días con ese criterio.\n"
                "Intenta con otro profesional o más adelante."
            )
            return

        # Tomar hasta 3 slots por día, máx 9 total
        from ..bot.keyboards import AVAILABILITY_KEYBOARD
        await query.edit_message_text(
            "📅 <b>Horarios disponibles</b>\n\nElige tu horario preferido:",
            parse_mode="HTML",
            reply_markup=AVAILABILITY_KEYBOARD(slots[:9]),
        )
    except Exception as e:
        logger.exception("availability_error", error=str(e))
        await query.edit_message_text("❌ Error consultando disponibilidad. Intenta de nuevo.")


async def _handle_slot_action(query, params, context):
    """Maneja selección de slot horario (nueva reserva o reprogramación)."""
    if len(params) < 2:
        return

    slot_index = int(params[0])
    slot_id = params[1]  # formato: service_id|professional_id|iso_datetime

    # Parsear slot_id
    parts = slot_id.split("|")
    service_id = parts[0]
    professional_id = parts[1] if parts[1] != "none" else None
    start_time = parts[2]

    # Verificar si estamos en modo reprogramación
    if context.user_data.get("awaiting_reschedule_datetime"):
        booking_id = context.user_data.get("reschedule_booking_id")
        if not booking_id:
            await query.edit_message_text("❌ Sesión expirada. Vuelve a intentarlo.")
            return

        # Guardar nueva hora para reprogramación
        context.user_data["reschedule_new_time"] = start_time
        context.user_data["awaiting_reschedule_datetime"] = False

        # Obtener reserva para mostrar resumen
        from ..booking.client import get_booking
        booking = await get_booking(booking_id=booking_id)
        
        if not booking or not booking.get("bookings"):
            await query.edit_message_text("❌ Reserva no encontrada.")
            return

        b = booking["bookings"][0]
        
        from ..bot.keyboards import CONFIRM_KEYBOARD
        from ..booking.client import get_service
        service = await get_service(b.get("service_id"))

        await query.edit_message_text(
            f"🔄 <b>Confirmar Reprogramación</b>\n\n"
            f"📋 <b>Código:</b> {b.get('codigo', 'N/A')}\n"
            f"💇 <b>Servicio:</b> {b.get('service_name', 'N/A')}\n"
            f"📅 <b>Fecha actual:</b> {b.get('date_str', 'N/A')}\n"
            f"⏰ <b>Hora actual:</b> {b.get('time_str', 'N/A')}\n\n"
            f"📅 <b>Nueva fecha:</b> {start_time[:10]}\n"
            f"⏰ <b>Nueva hora:</b> {start_time[11:16]}\n\n"
            f"¿Confirmas el cambio?",
            parse_mode="HTML",
            reply_markup=CONFIRM_KEYBOARD,
        )
        return

    # Flujo normal: nueva reserva
    context.user_data["selected_slot"] = {
        "service_id": service_id,
        "professional_id": professional_id,
        "start_time": start_time,
    }

    # Pedir datos del cliente (si no los tenemos)
    from ..booking.client import get_client_by_telegram
    user_id = query.from_user.id
    client = await get_client_by_telegram(user_id)

    if client:
        # Ya tenemos datos, mostrar resumen para confirmar
        await _show_booking_summary(query, context, client)
    else:
        # Pedir datos
        await query.edit_message_text(
            "📝 <b>Datos para la reserva</b>\n\n"
            "Necesito tu nombre, teléfono y email para confirmar:\n\n"
            "Por favor escribe: <code>Nombre | Teléfono | Email</code>\n\n"
            "Ejemplo: <code>María González | +56912345678 | maria@email.com</code>",
            parse_mode="HTML",
        )
        context.user_data["awaiting_client_data"] = True


async def _handle_confirm_action(query, params, context):
    """Confirma la reserva."""
    action = params[0] if params else ""

    if action == "yes":
        slot = context.user_data.get("selected_slot")
        client_data = context.user_data.get("client_data")

        if not slot or not client_data:
            await query.edit_message_text("❌ Faltan datos. Vuelve a intentarlo con /start")
            return

        # Crear reserva via booking service
        from ..booking.client import create_booking
        from ..agent.tools.create_booking import create_booking as tool_create_booking

        try:
            result = await tool_create_booking(
                service_id=slot["service_id"],
                start_time=slot["start_time"],
                professional_id=slot["professional_id"],
                client=client_data,
            )

            if result.get("success"):
                await query.edit_message_text(
                    f"✅ <b>¡Reserva confirmada!</b>\n\n"
                    f"📋 <b>Código:</b> {result['booking']['codigo']}\n"
                    f"📅 <b>Fecha:</b> {result['booking']['inicio']}\n"
                    f"⏰ <b>Hora:</b> {result['booking']['inicio'][11:16]}\n"
                    f"💇 <b>Servicio:</b> {result['booking']['service_name']}\n"
                    f"👩‍💼 <b>Profesional:</b> {result['booking']['professional_name']}\n"
                    f"💰 <b>Precio:</b> ${result['booking']['precio']:,.0f} CLP\n\n"
                    f"Te enviamos la confirmación por email con el archivo .ics para tu calendario.\n\n"
                    f"¡Te esperamos! 💖",
                    parse_mode="HTML",
                )
                # Limpiar datos temporales
                context.user_data.pop("selected_slot", None)
                context.user_data.pop("client_data", None)
                context.user_data.pop("awaiting_client_data", None)
            else:
                await query.edit_message_text(
                    f"❌ No se pudo confirmar: {result.get('error', 'Error desconocido')}\n"
                    f"Intenta con otro horario."
                )
        except Exception as e:
            logger.exception("confirm_booking_error", error=str(e))
            await query.edit_message_text("❌ Error al confirmar. Intenta de nuevo.")

    elif action == "no":
        await query.edit_message_text(
            "❌ Reserva cancelada. Puedes empezar de nuevo con /start cuando quieras."
        )
        context.user_data.pop("selected_slot", None)


async def _handle_cancel_booking_action(query, params, context):
    """Cancela una reserva (con confirmación)."""
    booking_id = params[0] if params else None
    action = params[1] if len(params) > 1 else None
    
    if not booking_id:
        return

    # Si no hay acción, pedir confirmación
    if action != "confirm":
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Sí, cancelar", callback_data=f"cancel_booking:{booking_id}:confirm"),
                InlineKeyboardButton("❌ No, mantener", callback_data=f"cancel_booking:{booking_id}:no"),
            ],
        )
        
        # Obtener info de la reserva para mostrar
        from ..booking.client import get_booking
        booking = await get_booking(booking_id=booking_id)
        details = ""
        if booking and booking.get("bookings"):
            b = booking["bookings"][0]
            details = f"\n📋 <b>Código:</b> {b.get('codigo', 'N/A')}\n💇 <b>Servicio:</b> {b.get('service_name', 'N/A')}\n📅 <b>Fecha:</b> {b.get('date_str', 'N/A')}\n⏰ <b>Hora:</b> {b.get('time_str', 'N/A')}"
        
        await query.edit_message_text(
            f"⚠️ <b>Confirmar Cancelación</b>{details}\n\n"
            f"¿Estás seguro de que quieres cancelar esta reserva?\n\n"
            f"⚠️ <b>Política:</b>\n"
            f"• ≥24h antes: Sin cargo\n"
            f"• <24h antes: 50% cargo como abono\n"
            f"• No-show (no avisar): 100% cargo",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Sí, cancelar", callback_data=f"cancel_booking:{booking_id}:confirm"),
                    InlineKeyboardButton("❌ No, mantener", callback_data=f"cancel_booking:{booking_id}:no"),
                ],
            ]),
        )
        return

    # Acción confirmada
    if action == "no":
        await query.edit_message_text(
            "❌ Cancelación anulada. Tu reserva se mantiene."
        )
        return

    # action == "confirm"
    from ..agent.tools.cancel_booking import cancel_booking as tool_cancel_booking

    try:
        result = await tool_cancel_booking(booking_id=booking_id)
        if result.get("success"):
            await query.edit_message_text(
                "✅ <b>Reserva cancelada correctamente.</b>\n\n"
                "Si fue con más de 24h de anticipación, no hay cargo.\n"
                "Si fue con menos de 24h, se aplica el 50% del servicio como abono.\n\n"
                "Puedes agendar una nueva hora cuando quieras con /start"
            )
        else:
            await query.edit_message_text(f"❌ No se pudo cancelar: {result.get('error')}")
    except Exception as e:
        logger.exception("cancel_booking_error", error=str(e))
        await query.edit_message_text("❌ Error al cancelar. Intenta de nuevo.")


# ============================================================
# REPROGRAMAR RESERVA (FASE 4)
# ============================================================

async def _handle_reschedule_action(query, params, context):
    """Inicia flujo de reprogramación: pide nueva fecha/hora."""
    booking_id = params[0] if params else None
    if not booking_id:
        return

    context.user_data["reschedule_booking_id"] = booking_id

    # Obtener reserva actual para mostrar datos
    from ..booking.client import get_booking
    booking = await get_booking(booking_id=booking_id)
    
    if not booking or not booking.get("bookings"):
        await query.edit_message_text("❌ Reserva no encontrada.")
        return

    b = booking["bookings"][0]
    
    await query.edit_message_text(
        f"🔄 <b>Reprogramar Reserva</b>\n\n"
        f"📋 <b>Código:</b> {b.get('codigo', 'N/A')}\n"
        f"💇 <b>Servicio:</b> {b.get('service_name', 'N/A')}\n"
        f"📅 <b>Fecha actual:</b> {b.get('date_str', 'N/A')}\n"
        f"⏰ <b>Hora actual:</b> {b.get('time_str', 'N/A')}\n\n"
        f"¿A qué fecha y hora te gustaría cambiarla?\n\n"
        f"Escribe: <code>DD/MM/YYYY HH:MM</code>\n"
        f"Ejemplo: <code>25/11/2024 15:30</code>\n\n"
        f"O usa los botones para elegir día:",
        parse_mode="HTML",
        reply_markup=RESCHEDULE_DATE_KEYBOARD,
    )
    context.user_data["awaiting_reschedule_datetime"] = True


async def _handle_confirm_reschedule_action(query, params, context):
    """Confirma la reprogramación."""
    action = params[0] if params else ""

    if action == "yes":
        booking_id = context.user_data.get("reschedule_booking_id")
        new_start_time = context.user_data.get("reschedule_new_time")

        if not booking_id or not new_start_time:
            await query.edit_message_text("❌ Faltan datos. Vuelve a intentarlo.")
            return

        from ..agent.tools.reschedule_booking import reschedule_booking as tool_reschedule_booking

        try:
            result = await tool_reschedule_booking(
                booking_id=booking_id,
                new_start_time=new_start_time,
            )

            if result.get("success"):
                b = result.get("booking", {})
                await query.edit_message_text(
                    f"✅ <b>¡Reserva reprogramada!</b>\n\n"
                    f"📋 <b>Código:</b> {b.get('codigo', 'N/A')}\n"
                    f"📅 <b>Nueva fecha:</b> {b.get('date_str', 'N/A')}\n"
                    f"⏰ <b>Nueva hora:</b> {b.get('time_str', 'N/A')}\n"
                    f"💇 <b>Servicio:</b> {b.get('service_name', 'N/A')}\n"
                    f"👩‍💼 <b>Profesional:</b> {b.get('professional_name', 'N/A')}\n\n"
                    f"Te enviamos la confirmación actualizada por email con archivo .ics.\n\n"
                    f"¡Te esperamos! 💖",
                    parse_mode="HTML",
                )
            else:
                error = result.get('error', 'Error desconocido')
                alternatives = result.get('alternatives', [])
                if alternatives:
                    from ..bot.keyboards import AVAILABILITY_KEYBOARD
                    await query.edit_message_text(
                        f"❌ No se pudo reprogramar: {error}\n\n"
                        f"¿Te gustaría probar con uno de estos horarios?",
                        parse_mode="HTML",
                        reply_markup=AVAILABILITY_KEYBOARD(alternatives[:5]),
                    )
                else:
                    await query.edit_message_text(
                        f"❌ No se pudo reprogramar: {error}\n"
                        f"Intenta con otra fecha/hora."
                    )
        except Exception as e:
            logger.exception("reschedule_booking_error", error=str(e))
            await query.edit_message_text("❌ Error al reprogramar. Intenta de nuevo.")

    elif action == "no":
        await query.edit_message_text(
            "❌ Reprogramación cancelada. Tu reserva mantiene su horario original."
        )
        context.user_data.pop("reschedule_booking_id", None)
        context.user_data.pop("reschedule_new_time", None)
        context.user_data.pop("awaiting_reschedule_datetime", None)


async def _handle_reschedule_day_action(query, params, context):
    """Maneja selección de día para reprogramación."""
    date_str = params[0] if params else None
    if not date_str:
        return

    booking_id = context.user_data.get("reschedule_booking_id")
    if not booking_id:
        await query.edit_message_text("❌ Sesión expirada. Vuelve a intentarlo.")
        return

    # Obtener reserva para verificar servicio
    from ..booking.client import get_booking
    booking = await get_booking(booking_id=booking_id)
    
    if not booking or not booking.get("bookings"):
        await query.edit_message_text("❌ Reserva no encontrada.")
        return

    b = booking["bookings"][0]
    service_id = b.get("service_id")
    professional_id = b.get("professional_id")

    # Buscar slots disponibles para ese día
    from datetime import datetime, timedelta
    from ..booking.client import check_availability
    
    try:
        day_start = datetime.fromisoformat(date_str)
        day_end = day_start + timedelta(days=1)
        
        slots = await check_availability(service_id, day_start, day_end, professional_id)
        
        if not slots:
            await query.edit_message_text(
                f"😔 No hay disponibilidad para el {date_str}.\n"
                f"Intenta con otro día.",
                parse_mode="HTML",
                reply_markup=RESCHEDULE_DATE_KEYBOARD,
            )
            return

        # Filtrar solo slots del día seleccionado
        day_slots = [s for s in slots if s.get("date_str") == datetime.fromisoformat(date_str).strftime("%d/%m/%Y")]
        
        if not day_slots:
            await query.edit_message_text(
                f"😔 No hay horarios disponibles para el {date_str}.\n"
                f"Intenta con otro día.",
                parse_mode="HTML",
                reply_markup=RESCHEDULE_DATE_KEYBOARD,
            )
            return

        from ..bot.keyboards import AVAILABILITY_KEYBOARD
        await query.edit_message_text(
            f"📅 <b>Horarios disponibles para {date_str}</b>\n\nElige tu nuevo horario:",
            parse_mode="HTML",
            reply_markup=AVAILABILITY_KEYBOARD(day_slots[:9]),
        )
    except Exception as e:
        logger.exception("reschedule_day_error", error=str(e))
        await query.edit_message_text("❌ Error consultando disponibilidad. Intenta de nuevo.")


# ============================================================
# TECLADO PARA REPROGRAMACIÓN
# ============================================================
    """Teclado para elegir día de reprogramación (próximos 7 días)."""
    from datetime import datetime, timedelta
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    today = datetime.now()
    for i in range(7):
        day = datetime.now() + timedelta(days=i)
        if day.weekday() == 6:  # Domingo cerrado
            continue
        label = day.strftime("%a %d/%m")
        callback = f"reschedule_day:{day.strftime('%Y-%m-%d')}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback)])

    buttons.append([InlineKeyboardButton("« Volver", callback_data="menu:my_booking")])
    return InlineKeyboardMarkup(buttons)


# ============================================================
# MENSAJES DE TEXTO
# ============================================================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de texto libre."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")

    text = update.message.text.strip()
    logger.info("text_message", user_id=update.effective_user.id, text=text[:100])

    # Verificar estados especiales
    if context.user_data.get("awaiting_client_data"):
        await _handle_client_data_input(update, context, text)
        return

    if context.user_data.get("awaiting_handoff"):
        await _handle_handoff_input(update, context, text)
        return

    # Delegar al agente para lenguaje natural
    await _delegate_to_agent(update, context, text)


async def _handle_client_data_input(update, context, text):
    """Procesa entrada de datos del cliente: 'Nombre | Teléfono | Email'."""
    parts = [p.strip() for p in text.split("|")]
    if len(parts) != 3:
        await update.message.reply_html(
            "❌ Formato incorrecto. Usa: <code>Nombre | Teléfono | Email</code>\n"
            "Ejemplo: <code>María González | +56912345678 | maria@email.com</code>"
        )
        return

    nombre, telefono, email = parts

    # Validación básica
    if "@" not in email or "." not in email:
        await update.message.reply_html("❌ Email inválido. Intenta de nuevo.")
        return

    if len(telefono) < 8:
        await update.message.reply_html("❌ Teléfono muy corto. Incluye código de país (+569...).")
        return

    # Guardar datos
    client_data = {
        "nombre": nombre,
        "telefono": telefono,
        "email": email,
        "telegram_user_id": update.effective_user.id,
    }
    context.user_data["client_data"] = client_data
    context.user_data["awaiting_client_data"] = False

    # Mostrar resumen para confirmar
    slot = context.user_data.get("selected_slot")
    if slot:
        from ..booking.client import get_service, get_professional
        service = await get_service(slot["service_id"])
        professional = await get_professional(slot["professional_id"]) if slot["professional_id"] else None

        from ..bot.keyboards import CONFIRM_KEYBOARD
        await update.message.reply_html(
            f"📋 <b>Resumen de tu reserva</b>\n\n"
            f"👤 <b>Cliente:</b> {nombre}\n"
            f"📞 <b>Teléfono:</b> {telefono}\n"
            f"✉️ <b>Email:</b> {email}\n\n"
            f"💇 <b>Servicio:</b> {service['nombre'] if service else 'N/A'}\n"
            f"👩‍💼 <b>Profesional:</b> {professional['nombre'] if professional else 'Cualquiera disponible'}\n"
            f"📅 <b>Fecha/Hora:</b> {slot['start_time']}\n"
            f"💰 <b>Precio:</b> ${service['precio_clp']:,.0f} CLP\n\n"
            f"¿Confirmas la reserva?",
            parse_mode="HTML",
            reply_markup=CONFIRM_KEYBOARD,
        )


async def _handle_handoff_input(update, context, text):
    """Procesa mensaje para derivación a humano."""
    from ..notifier.telegram_admin import notify_admin_handoff

    await notify_admin_handoff(
        telegram_user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        summary=text,
    )

    context.user_data["awaiting_handoff"] = False

    await update.message.reply_html(
        "✅ <b>Tu mensaje ha sido enviado a nuestra administradora.</b>\n\n"
        "Ella te responderá a la brevedad por este mismo chat.\n\n"
        "Mientras tanto, ¿hay algo más en lo que pueda ayudarte?",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


# ============================================================
# MENSAJES DE VOZ (FASE 5)
# ============================================================

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja notas de voz - transcribe y delega al agente."""
    set_correlation_id(f"tg-{update.effective_user.id}-{update.update_id}")

    voice = update.message.voice
    if not voice:
        return

    logger.info("voice_message", user_id=update.effective_user.id, duration=voice.duration)

    # Verificar límite de duración (60s)
    if voice.duration > 60:
        await update.message.reply_html(
            "❌ La nota de voz es muy larga (máx. 60 segundos). "
            "Por favor graba un mensaje más corto o escríbelo."
        )
        return

    # Descargar archivo de voz
    file = await voice.get_file()
    voice_bytes = await file.download_as_bytearray()

    # Transcribir (STT)
    from ..voice.stt import transcribe_audio
    try:
        transcript = await transcribe_audio(bytes(voice_bytes))
    except Exception as e:
        logger.exception("stt_error", error=str(e))
        await update.message.reply_html("❌ No pude entender el audio. ¿Podrías escribirlo?")
        return

    if not transcript or len(transcript.strip()) < 3:
        await update.message.reply_html("❌ No se detectó voz clara. Intenta de nuevo o escríbelo.")
        return

    # Mostrar lo que entendió y pedir confirmación de datos críticos
    await update.message.reply_html(
        f"🎙 <b>Entendido:</b> <i>{transcript}</i>\n\n"
        f"¿Es correcto? Si quieres reservar, por favor confirma la fecha, hora y tu nombre."
    )

    # Delegar al agente con el texto transcrito
    await _delegate_to_agent(update, context, transcript)


# ============================================================
# DELEGACIÓN AL AGENTE
# ============================================================

async def _delegate_to_agent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> None:
    """Delega el turno al agente core."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    try:
        # Ejecutar turno del agente
        response = await run_agent_turn(
            user_id=user_id,
            chat_id=chat_id,
            user_text=user_text,
            context_data=context.user_data,
        )

        # Enviar respuesta del agente
        for msg in response.messages:
            if msg.type == "text":
                await update.message.reply_html(msg.content, reply_markup=msg.keyboard)
            elif msg.type == "voice" and context.user_data.get("voice_enabled"):
                # Enviar audio (fase 5)
                await update.message.reply_voice(msg.audio_bytes, caption=msg.caption)

    except Exception as e:
        logger.exception("agent_delegation_error", error=str(e))
        await update.message.reply_html(
            "❌ Tuve un problema procesando tu mensaje. "
            "Por favor intenta de nuevo o escribe /start para reiniciar."
        )


async def _delegate_to_agent_from_query(query, user_text: str) -> None:
    """Delega al agente desde un callback query (edita el mensaje)."""
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    try:
        response = await run_agent_turn(
            user_id=user_id,
            chat_id=chat_id,
            user_text=user_text,
            context_data={},
        )

        for msg in response.messages:
            if msg.type == "text":
                await query.edit_message_text(msg.content, parse_mode="HTML", reply_markup=msg.keyboard)
            # voice no soportado en edit_message_text

    except Exception as e:
        logger.exception("agent_delegation_from_query_error", error=str(e))
        await query.edit_message_text("❌ Error. Intenta de nuevo con /start")


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja errores no capturados."""
    logger.exception("telegram_error", error=str(context.error))

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_html(
                "❌ Ocurrió un error inesperado. Nuestro equipo fue notificado.\n"
                "Por favor intenta de nuevo en unos minutos o escribe /start."
            )
        except Exception:
            pass