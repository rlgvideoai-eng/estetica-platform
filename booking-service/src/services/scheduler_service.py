"""Scheduler Service - Recordatorios automáticos con APScheduler."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.booking import Booking, BookingStatus
from ..models.client import Client
from ..models.service import Service
from ..models.professional import Professional
from ..services.notification_service import NotificationService
from ..services.calendar_service import CalendarService
from ..utils.timezone import now_santiago, to_santiago

logger = logging.getLogger(__name__)


class SchedulerService:
    """Gestiona recordatorios automáticos y tareas programadas."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.scheduler = AsyncIOScheduler(timezone="America/Santiago")
        self._running = False

    async def start(self):
        """Inicia el scheduler y programa jobs recurrentes."""
        if self._running:
            return

        # Job diario para recordatorios 24h
        self.scheduler.add_job(
            self._check_and_send_reminders,
            CronTrigger(hour=9, minute=0, timezone="America/Santiago"),  # 9 AM diario
            id="daily_reminders",
            name="Recordatorios 24h antes",
            replace_existing=True,
        )

        # Job cada 30 min para sincronizar Google Calendar (lectura free/busy)
        self.scheduler.add_job(
            self._sync_calendar_freebusy,
            CronTrigger(minute="*/30", timezone="America/Santiago"),
            id="sync_freebusy",
            name="Sync free/busy Google Calendar",
            replace_existing=True,
        )

        # Job diario a medianoche para limpiar reservas antiguas (opcional)
        self.scheduler.add_job(
            self._cleanup_old_bookings,
            CronTrigger(hour=2, minute=0, timezone="America/Santiago"),
            id="cleanup_old_bookings",
            name="Limpieza reservas antiguas",
            replace_existing=True,
        )

        self.scheduler.start()
        self._running = True
        logger.info("scheduler_started", jobs=list(self.scheduler.get_jobs()))

    async def shutdown(self):
        """Detiene el scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("scheduler_stopped")

    # ============================================================
    # JOBS PRINCIPALES
    # ============================================================

    async def _check_and_send_reminders(self):
        """Envía recordatorios 24h antes de cada reserva."""
        logger.info("reminder_job_started")
        
        async with self.session_factory() as session:
            notification = NotificationService(session)
            
            # Buscar reservas confirmadas para mañana (24h window)
            now_santiago = now_santiago()
            tomorrow_start = (now_santiago + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_end = tomorrow_start + timedelta(days=1)

            # Convertir a UTC para query
            from ..utils.timezone import to_utc
            tomorrow_start_utc = to_utc(tomorrow_start)
            tomorrow_end_utc = to_utc(tomorrow_end)

            stmt = select(Booking).where(
                and_(
                    Booking.estado == BookingStatus.CONFIRMED,
                    Booking.inicio >= tomorrow_start_utc,
                    Booking.inicio < tomorrow_end_utc,
                )
            )
            result = await session.execute(stmt)
            bookings = list(result.scalars().all())

            logger.info("reminders_to_send", count=len(bookings))

            for booking in bookings:
                try:
                    await self._send_booking_reminder(session, notification, booking)
                except Exception as e:
                    logger.exception("reminder_send_failed", booking_id=str(booking.id), error=str(e))

            # Recordatorio adicional por Telegram
            await self._send_telegram_reminders(session, bookings)

    async def _send_booking_reminder(self, session, notification: NotificationService, booking):
        """Envía recordatorio email + .ics para una reserva."""
        from ..utils.ics import generate_ics
        
        client = await session.get(Client, booking.client_id)
        service = await session.get(Service, booking.service_id)
        professional = await session.get(Professional, booking.professional_id) if booking.professional_id else None

        if not client or not service:
            return

        ics_content = generate_ics(booking, service, professional)

        # Email recordatorio
        await notification.send_booking_reminder(
            client_email=client.email,
            client_name=client.nombre,
            booking={
                "codigo": booking.codigo,
                "service_name": service.nombre,
                "professional_name": professional.nombre if professional else "Por confirmar",
                "date_str": to_santiago(booking.inicio).strftime("%d/%m/%Y"),
                "time_str": to_santiago(booking.inicio).strftime("%H:%M"),
            },
            ics_content=ics_content,
        )

        # Notificar a admin
        from ..notifier.telegram_admin import notify_admin_reminder_sent
        await notify_admin_reminder_sent({
            "codigo": booking.codigo,
            "client_name": client.nombre,
            "service_name": service.nombre,
            "time_str": to_santiago(booking.inicio).strftime("%H:%M"),
        })

        logger.info("reminder_sent", booking_id=str(booking.id), client_email=client.email)

    async def _send_telegram_reminders(self, session, bookings):
        """Envía recordatorios por Telegram a las clientas."""
        from ..notifier.telegram_admin import notify_client_reminder
        
        for booking in bookings:
            client = await session.get(Client, booking.client_id)
            service = await session.get(Service, booking.service_id)
            
            if client and client.telegram_user_id:
                try:
                    await notify_client_reminder(
                        telegram_user_id=client.telegram_user_id,
                        booking={
                            "codigo": booking.codigo,
                            "service_name": service.nombre if service else "N/A",
                            "date_str": to_santiago(booking.inicio).strftime("%d/%m/%Y"),
                            "time_str": to_santiago(booking.inicio).strftime("%H:%M"),
                            "professional_name": "Tu profesional",  # Se puede mejorar cargando professional
                        },
                    )
                    logger.info("telegram_reminder_sent", booking_id=str(booking.id))
                except Exception as e:
                    logger.exception("telegram_reminder_failed", booking_id=str(booking.id), error=str(e))

    async def _sync_calendar_freebusy(self):
        """Sincroniza free/busy desde Google Calendar para detectar citas manuales."""
        async with self.session_factory() as session:
            calendar = CalendarService(session)
            
            # Obtener profesionales con Google Calendar configurado
            from ..models.professional import Professional
            stmt = select(Professional).where(
                and_(
                    Professional.activo == True,
                    Professional.google_calendar_id.is_not(None),
                )
            )
            result = await session.execute(stmt)
            professionals = list(result.scalars().all())

            time_min = now_santiago()
            time_max = time_min + timedelta(days=7)

            total_synced = 0
            for prof in professionals:
                synced = await calendar.sync_bookings_from_calendar(prof.id, time_min, time_max)
                total_synced += prof.id if synced else 0

            if total_synced > 0:
                logger.info("freebusy_sync_completed", total_synced=total_synced)

    async def _cleanup_old_bookings(self):
        """Limpia reservas antiguas (opcional: marcar no_show automáticamente)."""
        async with self.session_factory() as session:
            now_utc = datetime.now().astimezone()
            cutoff = now_utc - timedelta(days=1)  # Reservas de ayer sin completar

            stmt = select(Booking).where(
                and_(
                    Booking.estado.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                    Booking.fin < cutoff,
                )
            )
            result = await session.execute(stmt)
            old_bookings = list(result.scalars().all())

            for booking in old_bookings:
                booking.estado = BookingStatus.NO_SHOW
                booking.notas = (booking.notas or "") + "\nMarcado automáticamente como no_show por scheduler"

            if old_bookings:
                await session.flush()
                logger.info("no_show_auto_marked", count=len(old_bookings))

    # ============================================================
    # PROGRAMACIÓN DE RECORDATORIOS ESPECÍFICOS (para reservas individuales)
    # ============================================================

    async def schedule_booking_reminder(self, booking_id: UUID, hours_before: int = 24):
        """Programa recordatorio específico para una reserva (job único)."""
        async with self.session_factory() as session:
            booking = await session.get(Booking, booking_id)
            if not booking or booking.estado != BookingStatus.CONFIRMED:
                return

            reminder_time = to_santiago(booking.inicio) - timedelta(hours=hours_before)
            now = now_santiago()
            
            if reminder_time <= now:
                logger.warning("reminder_time_past", booking_id=str(booking_id))
                return

            # Convertir a UTC para APScheduler
            from ..utils.timezone import to_utc
            reminder_utc = to_utc(reminder_time)

            job_id = f"reminder_{booking_id}_{hours_before}h"
            
            self.scheduler.add_job(
                self._send_single_reminder,
                DateTrigger(run_date=reminder_utc, timezone="America/Santiago"),
                args=[booking_id, hours_before],
                id=job_id,
                name=f"Recordatorio {hours_before}h - {booking.codigo}",
                replace_existing=True,
            )
            logger.info("reminder_scheduled", booking_id=str(booking_id), run_at=reminder_utc.isoformat())

    async def _send_single_reminder(self, booking_id: UUID, hours_before: int):
        """Envía recordatorio individual (para job programado)."""
        async with self.session_factory() as session:
            notification = NotificationService(session)
            booking = await session.get(Booking, booking_id)
            if not booking or booking.estado != BookingStatus.CONFIRMED:
                return
            
            await self._send_booking_reminder(session, notification, booking)

    async def cancel_booking_reminders(self, booking_id: UUID):
        """Cancela todos los recordatorios programados para una reserva."""
        job_id = f"reminder_{booking_id}_24h"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info("reminder_cancelled", booking_id=str(booking_id))


# Instancia global (se inicializa en main.py)
scheduler_service: Optional[SchedulerService] = None


async def get_scheduler_service(session_factory) -> SchedulerService:
    """Obtiene o crea la instancia global del scheduler."""
    global scheduler_service
    if scheduler_service is None:
        scheduler_service = SchedulerService(session_factory)
    return scheduler_service