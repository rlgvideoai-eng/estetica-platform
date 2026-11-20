"""Calendar Service - Integración con Google Calendar (OAuth 2.0 real)."""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import settings
from ..models.booking import Booking
from ..models.service import Service
from ..models.professional import Professional
from ..models.client import Client
from ..db.session import get_session

logger = logging.getLogger(__name__)


class CalendarService:
    """Gestiona sincronización bidireccional con Google Calendar."""

    def __init__(self, session):
        self.session = session
        self._service = None

    def _get_credentials(self) -> Credentials:
        """Crea credenciales OAuth2 con refresh token."""
        return Credentials(
            token=None,  # Se renueva automáticamente
            refresh_token=settings.google_refresh_token,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )

    def _get_calendar_service(self):
        """Obtiene o crea el cliente de Google Calendar API."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    async def _load_booking_relations(self, booking: Booking) -> tuple[Service, Optional[Professional], Client]:
        """Carga relaciones necesarias para el evento."""
        service = await self.session.get(Service, booking.service_id)
        professional = await self.session.get(Professional, booking.professional_id) if booking.professional_id else None
        client = await self.session.get(Client, booking.client_id)
        return service, professional, client

    async def create_event(self, booking: Booking) -> Optional[str]:
        """Crea evento en Google Calendar. Retorna event_id."""
        if not settings.google_client_id or not settings.google_refresh_token:
            logger.warning("google_calendar_not_configured")
            return None

        try:
            service, professional, client = await self._load_booking_relations(booking)
            if not service or not client:
                logger.error("missing_relations_for_calendar", booking_id=str(booking.id))
                return None

            event = self._build_event(booking, service, professional, client)
            calendar_id = professional.google_calendar_id if professional and professional.google_calendar_id else settings.google_calendar_id

            service_api = self._get_calendar_service()
            created = service_api.events().insert(calendarId=calendar_id, body=event, sendUpdates="all").execute()
            
            logger.info("google_calendar_event_created", event_id=created.get("id"), booking_id=str(booking.id))
            return created.get("id")

        except HttpError as e:
            logger.exception("google_calendar_create_error", error=str(e), status=e.resp.status)
            raise
        except Exception as e:
            logger.exception("google_calendar_unexpected_error", error=str(e))
            raise

    async def update_event(self, booking: Booking) -> bool:
        """Actualiza evento existente en Google Calendar."""
        if not booking.google_event_id:
            logger.warning("no_google_event_id_to_update", booking_id=str(booking.id))
            return False

        if not settings.google_client_id or not settings.google_refresh_token:
            return False

        try:
            service, professional, client = await self._load_booking_relations(booking)
            if not service or not client:
                return False

            event = self._build_event(booking, service, professional, client)
            calendar_id = professional.google_calendar_id if professional and professional.google_calendar_id else settings.google_calendar_id

            service_api = self._get_calendar_service()
            service_api.events().update(
                calendarId=calendar_id,
                eventId=booking.google_event_id,
                body=event,
                sendUpdates="all",
            ).execute()
            
            logger.info("google_calendar_event_updated", event_id=booking.google_event_id)
            return True

        except HttpError as e:
            if e.resp.status == 404:
                # Evento no existe, crear nuevo
                logger.warning("google_calendar_event_not_found", event_id=booking.google_event_id)
                new_id = await self.create_event(booking)
                if new_id:
                    from sqlalchemy import update
                    from ..models.booking import Booking as BookingModel
                    stmt = update(BookingModel).where(BookingModel.id == booking.id).values(google_event_id=new_id)
                    await self.session.execute(stmt)
                    await self.session.flush()
                    return True
            logger.exception("google_calendar_update_error", error=str(e))
            return False

    async def delete_event(self, booking: Booking) -> bool:
        """Elimina evento de Google Calendar."""
        if not booking.google_event_id:
            return False

        if not settings.google_client_id or not settings.google_refresh_token:
            return False

        try:
            service, professional, client = await self._load_booking_relations(booking)
            calendar_id = professional.google_calendar_id if professional and professional.google_calendar_id else settings.google_calendar_id

            service_api = self._get_calendar_service()
            service_api.events().delete(
                calendarId=calendar_id,
                eventId=booking.google_event_id,
                sendUpdates="all",
            ).execute()
            
            logger.info("google_calendar_event_deleted", event_id=booking.google_event_id)
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning("google_calendar_event_already_deleted", event_id=booking.google_event_id)
                return True
            logger.exception("google_calendar_delete_error", error=str(e))
            return False

    def _build_event(self, booking: Booking, service: Service, professional: Optional[Professional], client: Client) -> dict:
        """Construye el cuerpo del evento para Google Calendar."""
        summary = f"Ayudio - {service.nombre}"
        
        description_lines = [
            f"Cliente: {client.nombre}",
            f"Teléfono: {client.telefono}",
            f"Email: {client.email}",
            f"Código: {booking.codigo}",
            f"Origen: {booking.origen}",
            "",
            f"Servicio: {service.nombre}",
            f"Duración: {service.duracion_min} min",
            f"Precio: ${service.precio_clp:,.0f} CLP",
        ]
        if professional:
            description_lines.insert(5, f"Profesional: {professional.nombre}")
        
        description = "\n".join(description_lines)

        return {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": booking.inicio.isoformat(),
                "timeZone": "America/Santiago",
            },
            "end": {
                "dateTime": booking.fin.isoformat(),
                "timeZone": "America/Santiago",
            },
            "attendees": [
                {"email": client.email, "displayName": client.nombre},
            ] if client.email else [],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 1440},  # 24h antes
                    {"method": "popup", "minutes": 60},    # 1h antes
                ],
            },
            "colorId": "7",  # Color rosa para estética
            "location": "Av. Providencia 1234, Providencia, Santiago",
        }

    # ============================================================
    # SYNC DESDE GOOGLE CALENDAR (lectura free/busy)
    # ============================================================

    async def get_busy_slots(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
    ) -> list[dict]:
        """Obtiene slots ocupados desde Google Calendar (free/busy)."""
        if not settings.google_client_id or not settings.google_refresh_token:
            return []

        try:
            service_api = self._get_calendar_service()
            
            body = {
                "timeMin": time_min.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "items": [{"id": calendar_id}],
            }
            
            result = service_api.freebusy().query(body=body).execute()
            busy = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
            
            return [
                {"start": b["start"], "end": b["end"]}
                for b in busy
            ]
        except HttpError as e:
            logger.exception("google_calendar_freebusy_error", error=str(e))
            return []

    async def sync_bookings_from_calendar(
        self,
        professional_id: UUID,
        time_min: datetime,
        time_max: datetime,
    ) -> int:
        """Sincroniza eventos de Google Calendar como bloqueos (para citas creadas manualmente)."""
        professional = await self.session.get(Professional, professional_id)
        if not professional or not professional.google_calendar_id:
            return 0

        busy_slots = await self.get_busy_slots(
            professional.google_calendar_id,
            time_min,
            time_max,
        )

        synced = 0
        for slot in busy_slots:
            # Verificar si ya existe time_block para este slot
            from ..models.time_block import TimeBlock
            from sqlalchemy import select, and_
            
            start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
            
            existing = await self.session.execute(
                select(TimeBlock).where(
                    and_(
                        TimeBlock.professional_id == professional_id,
                        TimeBlock.inicio == start,
                        TimeBlock.fin == end,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Crear time_block
            block = TimeBlock(
                professional_id=professional_id,
                inicio=start,
                fin=end,
                motivo="Sincronizado desde Google Calendar",
            )
            self.session.add(block)
            synced += 1

        if synced > 0:
            await self.session.flush()
        
        logger.info("calendar_sync_completed", professional_id=str(professional_id), synced=synced)
        return synced