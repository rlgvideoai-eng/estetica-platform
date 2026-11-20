"""Notifier - Envío de emails (confirmaciones, recordatorios, cancelaciones)."""
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional

import aiosmtplib

from ..config import settings
from ..utils import get_logger, format_santiago, to_santiago

logger = get_logger(__name__)

# Plantilla base de email
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="es-CL">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #ec4899 0%, #db2777 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">💖 Ayudio</h1>
        <p style="color: #fce7f3; margin: 10px 0 0; font-size: 16px;">Centro de Estética</p>
    </div>
    <div style="background: #fff; padding: 30px; border: 1px solid #fce7f3; border-top: none; border-radius: 0 0 12px 12px;">
        {content}
    </div>
    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        <p>Av. Providencia 1234, Providencia, Santiago | +56 2 2233 4455 | hola@ayudio.cl</p>
        <p>© 2024 Ayudio. Todos los derechos reservados.</p>
    </div>
</body>
</html>
"""


class EmailNotifier:
    """Gestiona el envío de emails transaccionales."""

    def __init__(self):
        self.enabled = bool(settings.email_provider_key)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        ics_content: Optional[str] = None,
        ics_filename: str = "reserva.ics",
    ) -> bool:
        """Envía un email con contenido HTML y opcional adjunto .ics."""
        if not self.enabled:
            logger.info("email_disabled_simulated", to=to_email, subject=subject)
            return True

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.email_from
        message["To"] = to_email

        # Parte HTML
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        # Adjunto .ics si se proporciona
        if ics_content:
            ics_part = MIMEApplication(ics_content, _subtype="calendar")
            ics_part.add_header("Content-Disposition", f"attachment; filename={ics_filename}")
            message.attach(ics_part)

        try:
            await aiosmtplib.send(
                message,
                hostname="smtp.gmail.com",  # Configurable via settings
                port=587,
                start_tls=True,
                username=settings.email_from,
                password=settings.email_provider_key,
            )
            logger.info("email_sent", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.exception("email_send_error", to=to_email, subject=subject, error=str(e))
            return False

    def _render_template(self, content: str) -> str:
        """Renderiza la plantilla base con el contenido."""
        return EMAIL_TEMPLATE.format(subject="", content=content)


# Instancia global
email_notifier = EmailNotifier()


# ============================================================
# FUNCIONES DE CONVENIENCIA PARA EMAILS ESPECÍFICOS
# ============================================================

async def send_booking_confirmation(
    client_email: str,
    client_name: str,
    booking: Dict,
    ics_content: str,
) -> bool:
    """Envía confirmación de reserva con archivo .ics."""
    content = f"""
    <h2 style="color: #db2777; margin-top: 0;">¡Reserva Confirmada! ✅</h2>
    <p>Hola <strong>{client_name}</strong>,</p>
    <p>Tu reserva en <strong>Ayudio</strong> ha sido confirmada. Aquí están los detalles:</p>
    
    <div style="background: #fdf2f8; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px 0; font-weight: bold;">Código de reserva:</td><td style="text-align: right;">{booking.get('codigo', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Servicio:</td><td style="text-align: right;">{booking.get('service_name', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Profesional:</td><td style="text-align: right;">{booking.get('professional_name', 'Por confirmar')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Fecha:</td><td style="text-align: right;">{booking.get('date_str', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Hora:</td><td style="text-align: right;">{booking.get('time_str', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Duración:</td><td style="text-align: right;">{booking.get('duration', 'N/A')} min</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Precio:</td><td style="text-align: right;">${booking.get('precio', 0):,.0f} CLP</td></tr>
        </table>
    </div>

    <p><strong>Ubicación:</strong> Av. Providencia 1234, Providencia, Santiago</p>
    <p><strong>Teléfono:</strong> +56 2 2233 4455</p>

    <div style="background: #fef3c7; border-radius: 8px; padding: 15px; margin: 20px 0; border-left: 4px solid #f59e0b;">
        <p style="margin: 0;"><strong>📎 Adjunto:</strong> Este email incluye un archivo <code>.ics</code> para agregar la cita a tu calendario (Google Calendar, Apple Calendar, Outlook, etc.).</p>
    </div>

    <h3>Recordatorios importantes:</h3>
    <ul>
        <li>Llega 10 minutos antes de tu hora</li>
        <li>Para teñidos: no laves el cabello 24h antes</li>
        <li>Para uñas: llega sin esmalte</li>
        <li>Cancela/reprograma sin cargo hasta 24h antes</li>
    </ul>

    <p>Si necesitas cambiar o cancelar tu reserva, responde a este email o escríbenos por <a href="https://t.me/ayudio">Telegram</a>.</p>

    <p style="margin-top: 30px;">¡Te esperamos! 💖<br><strong>Equipo Ayudio</strong></p>
    """

    html = email_notifier._render_template(content)
    return await email_notifier.send_email(
        to_email=client_email,
        subject=f"✅ Reserva confirmada - {booking.get('codigo', 'Ayudio')}",
        html_content=html,
        ics_content=ics_content,
        ics_filename=f"ayudio_reserva_{booking.get('codigo', 'confirmacion')}.ics",
    )


async def send_booking_reminder(
    client_email: str,
    client_name: str,
    booking: Dict,
    ics_content: str,
) -> bool:
    """Envía recordatorio 24h antes."""
    content = f"""
    <h2 style="color: #db2777; margin-top: 0;">📅 Recordatorio: Tu cita es mañana</h2>
    <p>Hola <strong>{client_name}</strong>,</p>
    <p>Te recordamos tu reserva en <strong>Ayudio</strong> para mañana:</p>
    
    <div style="background: #fdf2f8; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px 0; font-weight: bold;">Servicio:</td><td style="text-align: right;">{booking.get('service_name', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Profesional:</td><td style="text-align: right;">{booking.get('professional_name', 'Por confirmar')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Fecha:</td><td style="text-align: right;">{booking.get('date_str', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Hora:</td><td style="text-align: right;">{booking.get('time_str', 'N/A')}</td></tr>
        </table>
    </div>

    <p>📍 <strong>Av. Providencia 1234, Providencia, Santiago</strong></p>

    <div style="background: #fef3c7; border-radius: 8px; padding: 15px; margin: 20px 0; border-left: 4px solid #f59e0b;">
        <p style="margin: 0;"><strong>⚠️ Política de cancelación:</strong> Cambios o cancelaciones con menos de 24h tienen cargo del 50% del servicio. No-show (no asistir sin aviso) se cobra el 100%.</p>
    </div>

    <p>¿Necesitas cambiar tu hora? Responde a este email o escríbenos por <a href="https://t.me/ayudio">Telegram</a>.</p>

    <p style="margin-top: 30px;">¡Te esperamos! 💖<br><strong>Equipo Ayudio</strong></p>
    """

    html = email_notifier._render_template(content)
    return await email_notifier.send_email(
        to_email=client_email,
        subject=f"📅 Recordatorio: Tu cita en Ayudio mañana - {booking.get('service_name', '')}",
        html_content=html,
        ics_content=ics_content,
        ics_filename=f"ayudio_recordatorio_{booking.get('codigo', 'recordatorio')}.ics",
    )


async def send_booking_cancellation(
    client_email: str,
    client_name: str,
    booking: Dict,
    cancelled_by: str = "client",
    charge_applied: bool = False,
) -> bool:
    """Envía notificación de cancelación."""
    charge_text = ""
    if charge_applied:
        charge_text = """
        <div style="background: #fef2f2; border-radius: 8px; padding: 15px; margin: 20px 0; border-left: 4px solid #ef4444;">
            <p style="margin: 0;"><strong>⚠️ Cargo aplicado:</strong> Al cancelar con menos de 24 horas de anticipación, se aplica el 50% del servicio ($${precio_50:,.0f} CLP) como abono para tu próxima visita.</p>
        </div>
        """.replace("${precio_50:,.0f}", f"{booking.get('precio', 0) // 2:,}")

    content = f"""
    <h2 style="color: #db2777; margin-top: 0;">❌ Reserva Cancelada</h2>
    <p>Hola <strong>{client_name}</strong>,</p>
    <p>Tu reserva en <strong>Ayudio</strong> ha sido cancelada:</p>
    
    <div style="background: #fdf2f8; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px 0; font-weight: bold;">Código:</td><td style="text-align: right;">{booking.get('codigo', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Servicio:</td><td style="text-align: right;">{booking.get('service_name', 'N/A')}</td></tr>
            <tr><td style="padding: 8px 0; font-weight: bold;">Fecha/Hora:</td><td style="text-align: right;">{booking.get('date_str', 'N/A')} a las {booking.get('time_str', 'N/A')}</td></tr>
        </table>
    </div>

    {charge_text}

    <p>Cancelado por: <strong>{'Tú' if cancelled_by == 'client' else 'El centro'}</strong></p>

    <p>Puedes agendar una nueva hora cuando quieras por <a href="https://t.me/ayudio">Telegram</a> o respondiendo a este email.</p>

    <p style="margin-top: 30px;">¡Hasta pronto! 💖<br><strong>Equipo Ayudio</strong></p>
    """

    html = email_notifier._render_template(content)
    return await email_notifier.send_email(
        to_email=client_email,
        subject=f"❌ Reserva cancelada - {booking.get('codigo', 'Ayudio')}",
        html_content=html,
    )


async def send_booking_change(
    client_email: str,
    client_name: str,
    old_booking: Dict,
    new_booking: Dict,
    ics_content: str,
) -> bool:
    """Envía notificación de cambio de reserva."""
    content = f"""
    <h2 style="color: #db2777; margin-top: 0;">🔄 Reserva Reprogramada</h2>
    <p>Hola <strong>{client_name}</strong>,</p>
    <p>Tu reserva en <strong>Ayudio</strong> ha sido cambiada:</p>
    
    <div style="background: #fdf2f8; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #ef4444;">❌ Anterior</h3>
        <p>{old_booking.get('date_str', 'N/A')} a las {old_booking.get('time_str', 'N/A')} - {old_booking.get('service_name', 'N/A')}</p>
        
        <h3 style="color: #22c55e;">✅ Nueva</h3>
        <p>{new_booking.get('date_str', 'N/A')} a las {new_booking.get('time_str', 'N/A')} - {new_booking.get('service_name', 'N/A')}</p>
        <p><strong>Profesional:</strong> {new_booking.get('professional_name', 'Por confirmar')}</p>
    </div>

    <div style="background: #fef3c7; border-radius: 8px; padding: 15px; margin: 20px 0; border-left: 4px solid #f59e0b;">
        <p style="margin: 0;"><strong>📎 Adjunto:</strong> Nuevo archivo .ics actualizado para tu calendario.</p>
    </div>

    <p>Si hay algún problema, contáctanos por <a href="https://t.me/ayudio">Telegram</a> o responde a este email.</p>

    <p style="margin-top: 30px;">¡Te esperamos! 💖<br><strong>Equipo Ayudio</strong></p>
    """

    html = email_notifier._render_template(content)
    return await email_notifier.send_email(
        to_email=client_email,
        subject=f"🔄 Reserva reprogramada - {new_booking.get('codigo', 'Ayudio')}",
        html_content=html,
        ics_content=ics_content,
        ics_filename=f"ayudio_reprogramada_{new_booking.get('codigo', 'cambio')}.ics",
    )


async def send_admin_notification(
    subject: str,
    message: str,
    booking: Optional[Dict] = None,
) -> bool:
    """Envía notificación a la administradora."""
    if not settings.admin_email:
        return False

    content = f"""
    <h2 style="color: #db2777; margin-top: 0;">🔔 Notificación Administrativa</h2>
    <p>{message}</p>
    """

    if booking:
        content += f"""
        <div style="background: #fdf2f8; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px 0; font-weight: bold;">Código:</td><td style="text-align: right;">{booking.get('codigo', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Cliente:</td><td style="text-align: right;">{booking.get('client_name', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Servicio:</td><td style="text-align: right;">{booking.get('service_name', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Fecha/Hora:</td><td style="text-align: right;">{booking.get('date_str', 'N/A')} {booking.get('time_str', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Estado:</td><td style="text-align: right;">{booking.get('estado', 'N/A')}</td></tr>
            </table>
        </div>
        """

    content += "<p>Revisa el panel de administración o el chat de Telegram para más detalles.</p>"

    html = email_notifier._render_template(content)
    return await email_notifier.send_email(
        to_email=settings.admin_email,
        subject=f"[Ayudio Admin] {subject}",
        html_content=html,
    )