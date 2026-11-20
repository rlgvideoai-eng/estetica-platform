"""Notification Service - Envío de notificaciones (email, Telegram admin + client)."""
import logging
from typing import Optional

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from ..config import settings
from ..notifier.telegram_admin import (
    notify_admin_handoff,
    notify_admin_new_booking,
    notify_admin_booking_change,
    notify_admin_reminder_sent,
)
from ..notifier.telegram_client import (
    notify_client_reminder,
    notify_client_booking_change,
    notify_client_cancellation,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Gestiona el envío de notificaciones."""

    def __init__(self, session):
        self.session = session

    # ============================================================
    # EMAIL
    # ============================================================

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        ics_content: Optional[str] = None,
        ics_filename: str = "reserva.ics",
    ) -> bool:
        """Envía email con contenido HTML y opcional adjunto .ics."""
        if not settings.email_provider_key:
            logger.info("email_disabled_simulated", to=to_email, subject=subject)
            return True

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.email_from
        message["To"] = to_email

        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        if ics_content:
            ics_part = MIMEApplication(ics_content, _subtype="calendar")
            ics_part.add_header("Content-Disposition", f'attachment; filename="{ics_filename}"')
            message.attach(ics_part)

        try:
            await aiosmtplib.send(
                message,
                hostname="smtp.gmail.com",
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

    def _base_template(self, content: str) -> str:
        """Plantilla base HTML para emails."""
        return f"""
        <!DOCTYPE html>
        <html lang="es-CL">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
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

    async def send_booking_confirmation(
        self,
        client_email: str,
        client_name: str,
        booking: dict,
        ics_content: str,
    ) -> bool:
        """Envía confirmación de reserva con .ics."""
        content = f"""
        <h2 style="color: #db2777; margin-top: 0;">¡Reserva Confirmada! ✅</h2>
        <p>Hola <strong>{client_name}</strong>,</p>
        <p>Tu reserva en <strong>Ayudio</strong> ha sido confirmada. Aquí están los detalles:</p>
        
        <div style="background: #fdf2f8; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px 0; font-weight: bold;">Código:</td><td style="text-align: right;">{booking.get('codigo', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Servicio:</td><td style="text-align: right;">{booking.get('service_name', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Profesional:</td><td style="text-align: right;">{booking.get('professional_name', 'Por confirmar')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Fecha:</td><td style="text-align: right;">{booking.get('date_str', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Hora:</td><td style="text-align: right;">{booking.get('time_str', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Duración:</td><td style="text-align: right;">{booking.get('duration', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Precio:</td><td style="text-align: right;">${booking.get('precio', 0):,.0f} CLP</td></tr>
            </table>
        </div>

        <p><strong>Ubicación:</strong> Av. Providencia 1234, Providencia, Santiago</p>
        <p><strong>Teléfono:</strong> +56 2 2233 4455</p>

        <div style="background: #fef3c7; border-radius: 8px; padding: 15px; margin: 20px 0; border-left: 4px solid #f59e0b;">
            <p style="margin: 0;"><strong>📎 Adjunto:</strong> Archivo <code>.ics</code> para agregar a tu calendario.</p>
        </div>

        <h3>Recordatorios:</h3>
        <ul>
            <li>Llega 10 minutos antes</li>
            <li>Para teñidos: no lavar cabello 24h antes</li>
            <li>Para uñas: llegar sin esmalte</li>
            <li>Cancelar/reprogramar sin cargo hasta 24h antes</li>
        </ul>

        <p>Cambios o cancelaciones: <a href="https://t.me/ayudio">Telegram</a> o responde a este email.</p>

        <p style="margin-top: 30px;">¡Te esperamos! 💖<br><strong>Equipo Ayudio</strong></p>
        """

        html = self._base_template(content)
        return await self._send_email(
            to_email=client_email,
            subject=f"✅ Reserva confirmada - {booking.get('codigo', 'Ayudio')}",
            html_content=html,
            ics_content=ics_content,
            ics_filename=f"ayudio_reserva_{booking.get('codigo', 'confirmacion')}.ics",
        )

    async def send_booking_reminder(
        self,
        client_email: str,
        client_name: str,
        booking: dict,
        ics_content: str,
        telegram_user_id: Optional[int] = None,
    ) -> bool:
        """Envía recordatorio 24h antes (email + Telegram)."""
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
            <p style="margin: 0;"><strong>⚠️ Política:</strong> Cambios/cancelaciones <24h = 50% cargo. No-show = 100% cargo.</p>
        </div>

        <p>¿Cambiar hora? <a href="https://t.me/ayudio">Telegram</a> o responde a este email.</p>

        <p style="margin-top: 30px;">¡Te esperamos! 💖<br><strong>Equipo Ayudio</strong></p>
        """

        html = self._base_template(content)
        email_sent = await self._send_email(
            to_email=client_email,
            subject=f"📅 Recordatorio: Tu cita en Ayudio mañana - {booking.get('service_name', '')}",
            html_content=html,
            ics_content=ics_content,
            ics_filename=f"ayudio_recordatorio_{booking.get('codigo', 'recordatorio')}.ics",
        )

        # Enviar también por Telegram si tiene telegram_user_id
        telegram_sent = True
        if telegram_user_id:
            telegram_sent = await notify_client_reminder(
                telegram_user_id=telegram_user_id,
                booking={
                    "codigo": booking.get('codigo'),
                    "client_name": booking.get('client_name'),
                    "service_name": booking.get('service_name'),
                    "professional_name": booking.get('professional_name'),
                    "date_str": booking.get('date_str'),
                    "time_str": booking.get('time_str'),
                },
            )

        return email_sent and telegram_sent

    async def send_booking_cancellation(
        self,
        client_email: str,
        client_name: str,
        booking: dict,
        cancelled_by: str = "client",
        charge_applied: bool = False,
        telegram_user_id: Optional[int] = None,
    ) -> bool:
        """Envía notificación de cancelación (email + Telegram)."""
        charge_text = ""
        if charge_applied:
            charge_text = f"""
            <div style="background: #fef2f2; border-radius: 8px; padding: 15px; margin: 20px 0; border-left: 4px solid #ef4444;">
                <p style="margin: 0;"><strong>⚠️ Cargo aplicado:</strong> Al cancelar con menos de 24h, se aplica el 50% del servicio (${booking.get('precio', 0) // 2:,.0f} CLP) como abono.</p>
            </div>
            """

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
        <p>Agenda una nueva hora por <a href="https://t.me/ayudio">Telegram</a>.</p>

        <p style="margin-top: 30px;">¡Hasta pronto! 💖<br><strong>Equipo Ayudio</strong></p>
        """

        html = self._base_template(content)
        email_sent = await self._send_email(
            to_email=client_email,
            subject=f"❌ Reserva cancelada - {booking.get('codigo', 'Ayudio')}",
            html_content=html,
        )

        # Enviar también por Telegram
        telegram_sent = True
        if telegram_user_id:
            telegram_sent = await notify_client_cancellation(
                telegram_user_id=telegram_user_id,
                booking={
                    "codigo": booking.get('codigo'),
                    "service_name": booking.get('service_name'),
                    "date_str": booking.get('date_str'),
                    "time_str": booking.get('time_str'),
                    "precio": booking.get('precio'),
                },
                cancelled_by=cancelled_by,
                charge_applied=charge_applied,
            )

        return email_sent and telegram_sent

    async def send_booking_change(
        self,
        client_email: str,
        client_name: str,
        old_booking: dict,
        new_booking: dict,
        ics_content: str,
        telegram_user_id: Optional[int] = None,
    ) -> bool:
        """Envía notificación de cambio de reserva (email + Telegram)."""
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
            <p style="margin: 0;"><strong>📎 Adjunto:</strong> Nuevo archivo .ics actualizado.</p>
        </div>

        <p>¿Problemas? <a href="https://t.me/ayudio">Telegram</a> o responde a este email.</p>

        <p style="margin-top: 30px;">¡Te esperamos! 💖<br><strong>Equipo Ayudio</strong></p>
        """

        html = self._base_template(content)
        email_sent = await self._send_email(
            to_email=client_email,
            subject=f"🔄 Reserva reprogramada - {new_booking.get('codigo', 'Ayudio')}",
            html_content=html,
            ics_content=ics_content,
            ics_filename=f"ayudio_reprogramada_{new_booking.get('codigo', 'cambio')}.ics",
        )

        # Enviar también por Telegram
        telegram_sent = True
        if telegram_user_id:
            telegram_sent = await notify_client_booking_change(
                telegram_user_id=telegram_user_id,
                old_booking={
                    "date_str": old_booking.get('date_str'),
                    "time_str": old_booking.get('time_str'),
                    "service_name": old_booking.get('service_name'),
                },
                new_booking={
                    "codigo": new_booking.get('codigo'),
                    "date_str": new_booking.get('date_str'),
                    "time_str": new_booking.get('time_str'),
                    "service_name": new_booking.get('service_name'),
                    "professional_name": new_booking.get('professional_name'),
                    "client_name": new_booking.get('client_name'),
                },
            )

        return email_sent and telegram_sent

    # ============================================================
    # NOTIFICACIONES ADMIN (delegadas a telegram_admin)
    # ============================================================

    async def notify_admin_new_booking(self, booking: dict) -> bool:
        return await notify_admin_new_booking(booking)

    async def notify_admin_booking_change(self, action: str, booking: dict, details: str = "") -> bool:
        return await notify_admin_booking_change(action, booking, details)

    async def notify_admin_handoff(self, telegram_user_id: int, username: str, first_name: str, summary: str) -> bool:
        return await notify_admin_handoff(telegram_user_id, username, first_name, summary)