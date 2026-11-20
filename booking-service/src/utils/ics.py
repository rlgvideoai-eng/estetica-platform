"""Generador de archivos .ICS para calendarios."""
import datetime
from typing import Optional
from uuid import UUID

from icalendar import Calendar, Event, vText

from ..models.booking import Booking
from ..models.service import Service
from ..models.professional import Professional
from ..utils.timezone import format_santiago


def generate_ics(
    booking: Booking,
    service: Service,
    professional: Optional[Professional] = None,
) -> str:
    """Genera contenido .ics para una reserva."""
    cal = Calendar()
    cal.add("prodid", "-//Ayudio//Reserva//ES")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "REQUEST")
    cal.add("x-wr-calname", "Ayudio - Reservas")

    event = Event()
    event.add("uid", f"{booking.codigo}@ayudio.cl")
    event.add("dtstamp", datetime.datetime.now(datetime.timezone.utc))
    event.add("dtstart", booking.inicio)
    event.add("dtend", booking.fin)
    event.add("summary", f"Ayudio - {service.nombre}")
    event.add("description", _build_description(booking, service, professional))
    event.add("location", vText("Av. Providencia 1234, Providencia, Santiago"))
    event.add("status", "CONFIRMED")
    event.add("transp", "OPAQUE")

    # Alarmas
    from icalendar import Alarm
    alarm1 = Alarm()
    alarm1.add("action", "DISPLAY")
    alarm1.add("description", f"Recordatorio: {service.nombre} en Ayudio")
    alarm1.add("trigger", datetime.timedelta(hours=-24))  # 24h antes
    event.add_component(alarm1)

    alarm2 = Alarm()
    alarm2.add("action", "DISPLAY")
    alarm2.add("description", f"Próximo: {service.nombre} en 1 hora")
    alarm2.add("trigger", datetime.timedelta(hours=-1))  # 1h antes
    event.add_component(alarm2)

    cal.add_component(event)
    return cal.to_ical().decode("utf-8")


def _build_description(booking: Booking, service: Service, professional: Optional[Professional]) -> str:
    lines = [
        f"Reserva: {booking.codigo}",
        f"Servicio: {service.nombre}",
        f"Duración: {service.duracion_min} min",
        f"Precio: ${service.precio_clp:,.0f} CLP",
    ]
    if professional:
        lines.append(f"Profesional: {professional.nombre}")
    lines.append("")
    lines.append("Ubicación: Av. Providencia 1234, Providencia, Santiago")
    lines.append("Teléfono: +56 2 2233 4455")
    lines.append("Email: hola@ayudio.cl")
    lines.append("")
    lines.append("Política de cancelación:")
    lines.append("- Sin cargo hasta 24h antes")
    lines.append("- <24h: 50% cargo como abono")
    lines.append("- No-show: 100% cargo como abono")
    lines.append("")
    lines.append("Gestiona tu reserva en: https://t.me/ayudio")
    return "\n".join(lines)