"""Availability Service - Cálculo de slots disponibles (Core AG-2)."""
import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Service, Professional, BusinessHours, TimeBlock, Booking, BookingStatus
from ..schemas.availability import AvailabilitySlot
from ..config import settings
from ..utils.timezone import get_santiago_tz, combine_santiago, to_utc, santiago_date


class AvailabilityService:
    """Cálculo de disponibilidad: horario local ∩ horario profesional − reservas − bloqueos − eventos Google Calendar."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tz = get_santiago_tz()
        self.grid_minutes = settings.grid_size_minutes
        self.max_horizon_days = settings.booking_max_horizon_days
        self.min_advance_hours = settings.cancel_min_hours  # reusamos para anticipación mínima

    async def get_slots(
        self,
        service_id: UUID,
        from_date: datetime.datetime,
        to_date: datetime.datetime,
        professional_id: Optional[UUID] = None,
    ) -> List[AvailabilitySlot]:
        """Calcula slots disponibles para un servicio en un rango."""

        # 1. Obtener servicio
        service = await self.session.get(Service, service_id)
        if not service or not service.activo:
            return []

        # 2. Obtener profesionales que hacen este servicio
        professionals = await self._get_professionals_for_service(service_id, professional_id)
        if not professionals:
            return []

        # 3. Obtener horarios del local
        business_hours = await self._get_business_hours()

        # 4. Obtener bloqueos (time_blocks)
        blocks = await self._get_time_blocks(from_date, to_date, professional_id)

        # 5. Obtener reservas existentes en el rango
        existing_bookings = await self._get_existing_bookings(from_date, to_date, professional_id)

        # 6. Para cada profesional, calcular slots día por día
        all_slots = []

        current_date = santiago_date(from_date)
        end_date = santiago_date(to_date)

        while current_date <= end_date:
            day_slots = await self._calculate_day_slots(
                current_date=current_date,
                service=service,
                professionals=professionals,
                business_hours=business_hours,
                blocks=blocks.get(current_date, []),
                existing_bookings=existing_bookings.get(current_date, []),
                professional_id=professional_id,
            )
            all_slots.extend(day_slots)
            current_date += datetime.timedelta(days=1)

        # Ordenar por fecha/hora y profesional
        all_slots.sort(key=lambda s: (s.start_iso, s.professional_id or ""))

        return all_slots

    async def _get_professionals_for_service(
        self,
        service_id: UUID,
        professional_id: Optional[UUID],
    ) -> List:
        from ..models import Professional, ProfessionalService

        stmt = (
            select(Professional)
            .join(ProfessionalService, Professional.id == ProfessionalService.professional_id)
            .where(
                ProfessionalService.service_id == service_id,
                Professional.activo == True,
            )
        )
        if professional_id:
            stmt = stmt.where(Professional.id == professional_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_business_hours(self) -> dict:
        from ..models import BusinessHours
        stmt = select(BusinessHours).where(BusinessHours.activo == True)
        result = await self.session.execute(stmt)
        hours = {}
        for bh in result.scalars().all():
            hours[bh.dia_semana] = bh.tramos  # 0=Dom, 1=Lun...
        return hours

    async def _get_time_blocks(
        self,
        from_date: datetime.datetime,
        to_date: datetime.datetime,
        professional_id: Optional[UUID],
    ) -> dict:
        from ..models import TimeBlock

        stmt = select(TimeBlock).where(
            TimeBlock.inicio < to_date,
            TimeBlock.fin > from_date,
        )
        if professional_id:
            stmt = stmt.where(
                or_(TimeBlock.professional_id == professional_id, TimeBlock.professional_id.is_(None))
            )
        else:
            stmt = stmt.where(TimeBlock.professional_id.is_(None))

        result = await self.session.execute(stmt)
        blocks = {}
        for block in result.scalars().all():
            date_key = santiago_date(block.inicio)
            if date_key not in blocks:
                blocks[date_key] = []
            blocks[date_key].append(block)
        return blocks

    async def _get_existing_bookings(
        self,
        from_date: datetime.datetime,
        to_date: datetime.datetime,
        professional_id: Optional[UUID],
    ) -> dict:
        stmt = select(Booking).where(
            Booking.inicio < to_date,
            Booking.fin > from_date,
            Booking.estado.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
        )
        if professional_id:
            stmt = stmt.where(Booking.professional_id == professional_id)

        result = await self.session.execute(stmt)
        bookings = {}
        for b in result.scalars().all():
            date_key = santiago_date(b.inicio)
            if date_key not in bookings:
                bookings[date_key] = []
            bookings[date_key].append(b)
        return bookings

    async def _calculate_day_slots(
        self,
        current_date: datetime.date,
        service,
        professionals: List,
        business_hours: dict,
        blocks: List,
        existing_bookings: List,
        professional_id: Optional[UUID],
    ) -> List[AvailabilitySlot]:
        """Calcula slots para un día específico."""
        import datetime

        slots = []
        day_of_week = (current_date.weekday() + 1) % 7  # 0=Dom, 1=Lun...

        # Horario del local para este día
        day_tramos = business_hours.get(day_of_week, [])
        if not day_tramos:
            return []  # Local cerrado

        # Verificar excepciones (feriados)
        from ..models import BusinessHours
        for bh in business_hours.get(day_of_week, []):
            pass  # Ya filtrado arriba

        # Para cada profesional
        for prof in professionals:
            # Horario de la profesional para este día
            prof_tramos = prof.horario_semanal.get(str(day_of_week), [])
            if not prof_tramos:
                continue

            # Intersección: local ∩ profesional
            intersected = self._intersect_tramos(day_tramos, prof_tramos)
            if not intersected:
                continue

            # Generar slots en la grilla
            for tramo in intersected:
                start_time = self._parse_time(tramo["start"])
                end_time = self._parse_time(tramo["end"])

                slot_start = datetime.datetime.combine(current_date, start_time)
                slot_end = datetime.datetime.combine(current_date, end_time)

                # Ajustar al grid
                slot_start = self._round_to_grid(slot_start)
                slot_end = self._round_to_grid(slot_end)

                # Generar slots dentro del tramo
                current = slot_start
                service_duration = service.duracion_min + service.prep_limpieza_min

                while current + datetime.timedelta(minutes=service_duration) <= slot_end:
                    slot_end_time = current + datetime.timedelta(minutes=service_duration)

                    # Verificar: no antes de anticipación mínima
                    now_santiago = datetime.datetime.now(self.tz)
                    min_start = now_santiago + datetime.timedelta(hours=self.min_advance_hours)
                    if current < min_start:
                        current += datetime.timedelta(minutes=self.grid_minutes)
                        continue

                    # Verificar bloqueos
                    if self._is_blocked(current, slot_end_time, blocks, professional_id):
                        current += datetime.timedelta(minutes=self.grid_minutes)
                        continue

                    # Verificar reservas existentes
                    if self._is_booked(current, slot_end_time, current, existing_bookings):
                        current += datetime.timedelta(minutes=self.grid_minutes)
                        continue

                    # Slot válido
                    slots.append(AvailabilitySlot(
                        start_iso=current.isoformat(),
                        end_iso=slot_end_time.isoformat(),
                        date_str=current.strftime("%d/%m/%Y"),
                        time_str=current.strftime("%H:%M"),
                        professional_id=prof.id,
                        professional_name=prof.nombre,
                    ))

                    current += datetime.timedelta(minutes=self.grid_minutes)

        return slots

    def _intersect_tramos(self, tramos_a, tramos_b):
        """Intersección de dos listas de tramos horarios."""
        intersected = []
        for a in tramos_a:
            a_start = self._parse_time(a["start"])
            a_end = self._parse_time(a["end"])
            for b in tramos_b:
                b_start = self._parse_time(b["start"])
                b_end = self._parse_time(b["end"])

                start = max(a_start, b_start)
                end = min(a_end, b_end)
                if start < end:
                    intersected.append({"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")})
        return intersected

    def _parse_time(self, time_str: str) -> datetime.time:
        return datetime.datetime.strptime(time_str, "%H:%M").time()

    def _round_to_grid(self, dt: datetime.datetime) -> datetime.datetime:
        """Redondea al grid más cercano (hacia arriba)."""
        minute = dt.minute
        remainder = minute % self.grid_minutes
        if remainder != 0:
            dt = dt + datetime.timedelta(minutes=self.grid_minutes - remainder)
        return dt.replace(second=0, microsecond=0)

    def _is_blocked(self, start, end, blocks, professional_id):
        for block in blocks:
            if block.professional_id is None or block.professional_id == professional_id:
                if start < block.fin and end > block.inicio:
                    return True
        return False

    def _is_booked(self, start, end, current_date, bookings):
        for booking in bookings:
            if start < booking.fin and end > booking.inicio:
                return True
        return False