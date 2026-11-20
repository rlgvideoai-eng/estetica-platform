"""Booking Service - Lógica de negocio para Reservas."""
import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Booking, Client, Service, Professional, BookingStatus
from ..schemas.booking import BookingCreateResponse, BookingResponse, AvailabilitySlot
from ..services.availability_service import AvailabilityService
from ..services.calendar_service import CalendarService
from ..services.notification_service import NotificationService
from ..utils.timezone import now_utc, to_utc, format_santiago
from ..config import settings


class BookingService:
    """Lógica de negocio para Reservas."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.availability = AvailabilityService(session)
        self.calendar = CalendarService(session)
        self.notifications = NotificationService(session)

    async def create_booking(
        self,
        service_id: UUID,
        start_time: datetime,
        professional_id: Optional[UUID],
        client: dict,
        idempotency_key: Optional[str] = None,
    ) -> "BookingCreateResponse":
        """Crea una reserva con idempotencia y validaciones."""

        # 1. Verificar idempotencia
        if idempotency_key:
            existing = await self._get_by_idempotency_key(idempotency_key)
            if existing:
                return BookingCreateResponse(
                    success=True,
                    booking=await self._to_response(existing),
                )

        # 2. Validar servicio
        service = await self.session.get(Service, service_id)
        if not service or not service.activo:
            return BookingCreateResponse(success=False, error="Servicio no encontrado o inactivo")

        # 3. Validar profesional
        if professional_id:
            prof = await self.session.get(Professional, professional_id)
            if not prof or not prof.activo:
                return BookingCreateResponse(success=False, error="Profesional no encontrado o inactivo")

        # 4. Validar hora de inicio (en UTC, convertido a Santiago)
        start_utc = to_utc(start_time)
        end_utc = start_utc + datetime.timedelta(minutes=service.duracion_min + service.prep_limpieza_min)

        # Verificar disponibilidad en tiempo real (double-check)
        slots = await self.availability.get_slots(
            service_id=service_id,
            from_date=start_utc,
            to_date=end_utc,
            professional_id=professional_id,
        )
        slot_match = any(s.start_iso == start_utc.isoformat() for s in slots)
        if not slot_match:
            # Buscar alternativas
            alternatives = await self.availability.get_slots(
                service_id=service_id,
                from_date=start_utc - datetime.timedelta(days=1),
                to_date=start_utc + datetime.timedelta(days=2),
                professional_id=professional_id,
            )
            return BookingCreateResponse(
                success=False,
                error="El horario ya no está disponible",
                alternatives=alternatives[:3],
            )

        # 5. Obtener o crear cliente
        client_obj = await self._get_or_create_client(client)

        # 6. Verificar límite de reservas activas por cliente
        active_count = await self._count_active_bookings(client_obj.id)
        if active_count >= settings.max_active_bookings_per_client:
            return BookingCreateResponse(
                success=False,
                error=f"Límite de {settings.max_active_bookings_per_client} reservas activas alcanzado",
            )

        # 7. Generar código legible
        codigo = self._generate_codigo()

        # 8. Crear reserva (estado PENDING hasta sync Google Calendar)
        booking = Booking(
            codigo=codigo,
            client_id=client_obj.id,
            service_id=service_id,
            professional_id=professional_id,
            inicio=start_utc,
            fin=end_utc,
            estado=BookingStatus.PENDING,
            origen="telegram",
            idempotency_key=idempotency_key,
        )
        self.session.add(booking)
        await self.session.flush()

        # 9. Sincronizar con Google Calendar (async, no bloqueante)
        try:
            google_event_id = await self.calendar.create_event(booking)
            booking.google_event_id = google_event_id
            booking.estado = BookingStatus.CONFIRMED
        except Exception as e:
            # Log error pero mantener reserva como PENDING para retry
            import logging
            logging.getLogger(__name__).warning("google_calendar_sync_failed", booking_id=str(booking.id), error=str(e))

        # 10. Notificaciones (async)
        await self._send_confirmation_notifications(booking)

        await self.session.flush()
        await self.session.refresh(booking)

        return BookingCreateResponse(
            success=True,
            booking=await self._to_response(booking),
        )

    async def get_booking(self, booking_id: UUID) -> Optional[Booking]:
        stmt = select(Booking).where(Booking.id == booking_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_booking(
        self,
        booking_id: UUID,
        data: dict,
    ) -> Optional[Booking]:
        booking = await self.get_booking(booking_id)
        if not booking:
            return None

        old_start = booking.inicio
        old_prof = booking.professional_id

        if "estado" in data:
            booking.estado = data["estado"]
        if "start_time" in data:
            booking.inicio = to_utc(data["start_time"])
            # Recalcular fin basado en servicio
            service = await self.session.get(Service, booking.service_id)
            booking.fin = booking.inicio + datetime.timedelta(
                minutes=service.duracion_min + service.prep_limpieza_min
            )
        if "professional_id" in data:
            booking.professional_id = data["professional_id"] if data["professional_id"] else None
        if "notas" in data:
            booking.notas = data["notas"]

        # Si cambió hora o profesional, re-sync Google Calendar
        if data.get("start_time") or data.get("professional_id"):
            try:
                if booking.google_event_id:
                    await self.calendar.update_event(booking)
                else:
                    google_event_id = await self.calendar.create_event(booking)
                    booking.google_event_id = google_event_id
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("google_calendar_update_failed", booking_id=str(booking.id), error=str(e))

        # Notificar cambio
        await self._send_change_notifications(booking, old_start, old_prof)

        await self.session.flush()
        await self.session.refresh(booking)
        return booking

    async def cancel_booking(
        self,
        booking_id: UUID,
        reason: Optional[str] = None,
    ) -> bool:
        booking = await self.get_booking(booking_id)
        if not booking:
            return False

        # Verificar política de cancelación
        now_santiago = datetime.datetime.now(self.availability.tz)
        booking_start = self.availability.to_santiago(booking.inicio)
        hours_diff = (booking_start - now_santiago).total_seconds() / 3600

        if hours_diff < settings.cancel_min_hours:
            # Cancelación tardía - marcar pero aplicar cargo
            booking.estado = BookingStatus.CANCELLED
            booking.notas = f"{booking.notas or ''}\nCancelación tardía (<{settings.cancel_min_hours}h): cargo 50%. Motivo: {reason or 'No especificado'}"
        else:
            booking.estado = BookingStatus.CANCELLED
            booking.notas = f"{booking.notas or ''}\nCancelado por cliente. Motivo: {reason or 'No especificado'}"

        # Eliminar evento Google Calendar
        if booking.google_event_id:
            try:
                await self.calendar.delete_event(booking)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("google_calendar_delete_failed", booking_id=str(booking.id), error=str(e))

        # Notificar cancelación
        await self._send_cancellation_notifications(booking, hours_diff < settings.cancel_min_hours)

        await self.session.flush()
        return True

    async def list_bookings(
        self,
        page: int = 1,
        size: int = 20,
        client_id: Optional[UUID] = None,
        estado: Optional[str] = None,
    ) -> Tuple[List[Booking], int]:
        stmt = select(Booking).order_by(Booking.inicio.desc())
        if client_id:
            stmt = stmt.where(Booking.client_id == client_id)
        if estado:
            stmt = stmt.where(Booking.estado == estado)

        # Count total
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    # ============================================================
    # HELPERS
    # ============================================================

    async def _get_or_create_client(self, client_data: dict) -> Client:
        """Obtiene cliente existente o crea nuevo."""
        if client_data.get("telegram_user_id"):
            stmt = select(Client).where(Client.telegram_user_id == client_data["telegram_user_id"])
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                # Actualizar datos si cambiaron
                for field in ["nombre", "telefono", "email"]:
                    if client_data.get(field):
                        setattr(existing, field, client_data[field])
                existing.consentimiento = True
                return existing

        # Buscar por email
        stmt = select(Client).where(Client.email == client_data["email"])
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            if client_data.get("telegram_user_id"):
                existing.telegram_user_id = client_data["telegram_user_id"]
            existing.consentimiento = True
            return existing

        # Crear nuevo
        new_client = Client(
            nombre=client_data["nombre"],
            telefono=client_data["telefono"],
            email=client_data["email"],
            telegram_user_id=client_data.get("telegram_user_id"),
            consentimiento=True,
            fecha_alta=datetime.datetime.now().astimezone(),
        )
        self.session.add(new_client)
        await self.session.flush()
        await self.session.refresh(new_client)
        return new_client

    async def _count_active_bookings(self, client_id: UUID) -> int:
        stmt = select(Booking).where(
            Booking.client_id == client_id,
            Booking.estado.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            Booking.inicio >= datetime.datetime.now().astimezone(),
        )
        result = await self.session.execute(stmt)
        return len(list(result.scalars().all()))

    def _generate_codigo(self) -> str:
        """Genera código legible: EST-YYYYMMDD-XXX"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        random_part = str(uuid.uuid4().int)[:3].zfill(3)
        return f"EST-{today}-{random_part}"

    async def _get_by_idempotency_key(self, key: str) -> Optional[Booking]:
        stmt = select(Booking).where(Booking.idempotency_key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _to_response(self, booking: Booking) -> "BookingResponse":
        service = await self.session.get(Service, booking.service_id)
        professional = await self.session.get(Professional, booking.professional_id) if booking.professional_id else None
        client = await self.session.get(Client, booking.client_id)

        return BookingResponse(
            id=booking.id,
            codigo=booking.codigo,
            service_id=booking.service_id,
            professional_id=booking.professional_id,
            client_id=booking.client_id,
            inicio=booking.inicio,
            fin=booking.fin,
            estado=booking.estado.value,
            origen=booking.origen,
            google_event_id=booking.google_event_id,
            idempotency_key=booking.idempotency_key,
            notas=booking.notas,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
        )

    async def _send_confirmation_notifications(self, booking: Booking):
        """Envía email de confirmación + notifica a admin + calendario."""
        client = await self.session.get(Client, booking.client_id)
        service = await self.session.get(Service, booking.service_id)
        professional = await self.session.get(Professional, booking.professional_id) if booking.professional_id else None

        # Generar .ics
        from ..utils.ics import generate_ics
        ics_content = generate_ics(booking, service, professional)

        # Email al cliente
        await self.notifications.send_booking_confirmation(
            client_email=client.email,
            client_name=client.nombre,
            booking={
                "codigo": booking.codigo,
                "service_name": service.nombre,
                "professional_name": professional.nombre if professional else "Por confirmar",
                "date_str": booking.inicio.strftime("%d/%m/%Y"),
                "time_str": booking.inicio.strftime("%H:%M"),
                "duration": f"{service.duracion_min + service.prep_limpieza_min} min",
                "precio": service.precio_clp,
            },
            ics_content=ics_content,
        )

        # Notificar a admin
        await self.notifications.notify_admin_new_booking({
            "id": str(booking.id),
            "codigo": booking.codigo,
            "client_name": client.nombre,
            "client_phone": client.telefono,
            "client_email": client.email,
            "service_name": service.nombre,
            "professional_name": professional.nombre if professional else "Por confirmar",
            "date_str": booking.inicio.strftime("%d/%m/%Y"),
            "time_str": booking.inicio.strftime("%H:%M"),
            "precio": service.precio_clp,
            "origen": booking.origen,
        })

    async def _send_change_notifications(self, booking: Booking, old_start, old_prof_id):
        """Notifica cambio de reserva (email + Telegram)."""
        client = await self.session.get(Client, booking.client_id)
        service = await self.session.get(Service, booking.service_id)
        professional = await self.session.get(Professional, booking.professional_id) if booking.professional_id else None

        # Generar .ics actualizado
        from ..utils.ics import generate_ics
        ics_content = generate_ics(booking, service, professional)

        # Email al cliente + Telegram
        telegram_user_id = client.telegram_user_id
        await self.notifications.send_booking_change(
            client_email=client.email,
            client_name=client.nombre,
            old_booking={
                "date_str": old_start.strftime("%d/%m/%Y"),
                "time_str": old_start.strftime("%H:%M"),
                "service_name": service.nombre,
            },
            new_booking={
                "codigo": booking.codigo,
                "date_str": booking.inicio.strftime("%d/%m/%Y"),
                "time_str": booking.inicio.strftime("%H:%M"),
                "service_name": service.nombre,
                "professional_name": professional.nombre if professional else "Por confirmar",
                "client_name": client.nombre,
            },
            ics_content=ics_content,
            telegram_user_id=telegram_user_id,
        )

        # Notificar a admin
        await self.notifications.notify_admin_booking_change(
            "rescheduled",
            {
                "codigo": booking.codigo,
                "client_name": client.nombre,
                "service_name": service.nombre,
                "date_str": booking.inicio.strftime("%d/%m/%Y"),
                "time_str": booking.inicio.strftime("%H:%M"),
            },
            f"Hora anterior: {old_start.strftime('%H:%M')} → Nueva: {booking.inicio.strftime('%H:%M')}"
        )

    async def _send_cancellation_notifications(self, booking: Booking, charge_applied: bool):
        """Notifica cancelación (email + Telegram)."""
        client = await self.session.get(Client, booking.client_id)
        service = await self.session.get(Service, booking.service_id)

        telegram_user_id = client.telegram_user_id

        await self.notifications.send_booking_cancellation(
            client_email=client.email,
            client_name=client.nombre,
            booking={
                "codigo": booking.codigo,
                "service_name": service.nombre,
                "date_str": booking.inicio.strftime("%d/%m/%Y"),
                "time_str": booking.inicio.strftime("%H:%M"),
                "precio": service.precio_clp,
            },
            cancelled_by="client",
            charge_applied=charge_applied,
            telegram_user_id=telegram_user_id,
        )

        await self.notifications.notify_admin_booking_change(
            "cancelled",
            {
                "codigo": booking.codigo,
                "client_name": client.nombre,
                "service_name": service.nombre,
                "date_str": booking.inicio.strftime("%d/%m/%Y"),
                "time_str": booking.inicio.strftime("%H:%M"),
            },
            f"Cargo aplicado: {'Sí (50%)' if charge_applied else 'No'}"
        )