"""Teclados inline para el bot de Telegram."""
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

MAIN_MENU_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📋 Ver servicios", callback_data="menu:services"),
        InlineKeyboardButton("📅 Agendar hora", callback_data="menu:book"),
    ],
    [
        InlineKeyboardButton("📋 Mi reserva", callback_data="menu:my_booking"),
        InlineKeyboardButton("👩‍💼 Hablar con una persona", callback_data="menu:human"),
    ],
    [
        InlineKeyboardButton("📍 Ubicación y horarios", callback_data="menu:location"),
    ],
])


# ============================================================
# SERVICIOS
# ============================================================

def SERVICE_KEYBOARD(services: Optional[List[dict]] = None) -> InlineKeyboardMarkup:
    """Teclado de categorías de servicios."""
    if services is None:
        # Servicios por defecto (mock)
        services = [
            {"id": "masajes", "name": "💆‍♀️ Masajes"},
            {"id": "lavados", "name": "🛁 Lavados y Tratamientos"},
            {"id": "tenidos", "name": "🎨 Teñidos y Color"},
            {"id": "unas", "name": "💅 Uñas"},
            {"id": "otros", "name": "✨ Otros Servicios"},
        ]

    buttons = []
    for svc in services:
        buttons.append([
            InlineKeyboardButton(svc["name"], callback_data=f"service:{svc['id']}")
        ])

    buttons.append([InlineKeyboardButton("« Volver", callback_data="menu:book")])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# PROFESIONALES
# ============================================================

def PROFESSIONAL_KEYBOARD(professionals: List[dict]) -> InlineKeyboardMarkup:
    """Teclado de selección de profesional."""
    buttons = []
    for prof in professionals:
        buttons.append([
            InlineKeyboardButton(
                f"👩‍💼 {prof['nombre']}",
                callback_data=f"prof:{prof['id']}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("🤷 Cualquiera disponible", callback_data="prof:auto"),
        InlineKeyboardButton("« Volver", callback_data="menu:services"),
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# DISPONIBILIDAD (SLOTS HORARIOS)
# ============================================================

def AVAILABILITY_KEYBOARD(slots: List[dict]) -> InlineKeyboardMarkup:
    """Teclado con slots horarios disponibles (máx 9)."""
    buttons = []

    for i, slot in enumerate(slots[:9]):
        # Formato: slot_index:service_id|professional_id|iso_datetime
        prof_name = slot.get("professional_name", "Cualquiera")
        slot_id = f"{slot['service_id']}|{slot['professional_id'] or 'none'}|{slot['start_iso']}"
        label = f"📅 {slot['date_str']} ⏰ {slot['time_str']} 👩‍💼 {prof_name}"

        buttons.append([
            InlineKeyboardButton(label, callback_data=f"slot:{i}:{slot_id}")
        ])

    buttons.append([
        InlineKeyboardButton("« Volver", callback_data="menu:book"),
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# CONFIRMACIÓN DE RESERVA
# ============================================================

CONFIRM_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Sí, confirmar", callback_data="confirm:yes"),
        InlineKeyboardButton("❌ No, cancelar", callback_data="confirm:no"),
    ],
])


# ============================================================
# CANCELAR RESERVA
# ============================================================

def CANCEL_BOOKING_KEYBOARD(booking_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sí, cancelar", callback_data=f"cancel_booking:{booking_id}:yes"),
            InlineKeyboardButton("❌ No, mantener", callback_data=f"cancel_booking:{booking_id}:no"),
        ],
    ])