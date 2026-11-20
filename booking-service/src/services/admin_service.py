"""Admin Service - Lógica de negocio para Panel Administrativo."""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Service, Professional, ProfessionalService, Client, Booking, BookingStatus
from ..schemas.admin import (
    AdminStats,
    BookingByDay,
    ServicePopularity,
    RevenueStats,
)


class AdminService:
    """Lógica de negocio para Panel Administrativo."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stats(self) -> dict:
        """Obtiene estadísticas generales para el dashboard."""
        now = datetime.now().astimezone()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Total de reservas
        total_bookings = await self.session.scalar(select(func.count(Booking.id)))

        # Reservas hoy
        bookings_today = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.inicio >= today_start)
        )

        # Reservas esta semana
        bookings_this_week = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.inicio >= week_start)
        )

        # Reservas este mes
        bookings_this_month = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.inicio >= month_start)
        )

        # Por estado
        pending = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.estado == "pending")
        )
        confirmed = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.estado == "confirmed")
        )
        cancelled = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.estado == "cancelled")
        )
        no_show = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.estado == "no_show")
        )

        # Ingresos
        total_revenue = await self.session.scalar(
            select(func.coalesce(func.sum(Service.precio_clp), 0))
            .select_from(Booking)
            .join(Service, Booking.service_id == Service.id)
            .where(Booking.estado == "confirmed")
        ) or 0

        revenue_this_month = await self.session.scalar(
            select(func.coalesce(func.sum(Service.precio_clp), 0))
            .select_from(Booking)
            .join(Service, Booking.service_id == Service.id)
            .where(
                and_(
                    Booking.estado == "confirmed",
                    Booking.inicio >= month_start,
                )
            )
        ) or 0

        # Clientes activos (con reserva en últimos 30 días)
        thirty_days_ago = datetime.now().astimezone() - timedelta(days=30)
        active_clients = await self.session.scalar(
            select(func.count(func.distinct(Booking.client_id)))
            .where(Booking.inicio >= thirty_days_ago)
        )

        # Profesionales activos
        active_professionals = await self.session.scalar(
            select(func.count(Professional.id)).where(Professional.activo == True)
        )

        # Servicios activos
        active_services = await self.session.scalar(
            select(func.count(Service.id)).where(Service.activo == True)
        )

        # Tasa de ocupación (reservas confirmadas / slots totales disponibles en últimos 30 días)
        # Simplificado: ratio de confirmadas vs totales
        total_recent = await self.session.scalar(
            select(func.count(Booking.id)).where(Booking.inicio >= thirty_days_ago)
        )
        confirmed_recent = await self.session.scalar(
            select(func.count(Booking.id)).where(
                and_(Booking.inicio >= thirty_days_ago, Booking.estado == "confirmed")
            )
        )
        occupancy_rate = (confirmed_recent / total_recent * 100) if total_recent > 0 else 0.0

        return {
            "total_bookings": total_bookings or 0,
            "bookings_today": bookings_today or 0,
            "bookings_this_week": bookings_this_week or 0,
            "bookings_this_month": bookings_this_month or 0,
            "pending_bookings": pending or 0,
            "confirmed_bookings": confirmed or 0,
            "cancelled_bookings": cancelled or 0,
            "no_show_bookings": no_show or 0,
            "total_revenue": total_revenue or 0,
            "revenue_this_month": revenue_this_month or 0,
            "active_clients": active_clients or 0,
            "active_professionals": active_professionals or 0,
            "active_services": active_services or 0,
            "occupancy_rate": round(occupancy_rate, 1),
            "avg_rating": None,
        }

    async def get_bookings_by_day(self, days: int = 30) -> List[dict]:
        """Reservas por día para gráficos."""
        since = datetime.now().astimezone() - timedelta(days=days)
        
        stmt = (
            select(
                func.date(Booking.inicio).label("date"),
                func.count(Booking.id).label("count"),
                func.coalesce(func.sum(Service.precio_clp), 0).label("revenue"),
            )
            .select_from(Booking)
            .join(Service, Booking.service_id == Service.id)
            .where(Booking.inicio >= since)
            .group_by(func.date(Booking.inicio))
            .order_by(func.date(Booking.inicio))
        )
        
        result = await self.session.execute(stmt)
        return [
            {
                "date": row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
                "count": row.count,
                "revenue": row.revenue or 0,
            }
            for row in result.all()
        ]

    async def get_services_popularity(self) -> List[dict]:
        """Popularidad de servicios."""
        stmt = (
            select(
                Service.id.label("service_id"),
                Service.nombre.label("service_name"),
                Service.categoria.label("category"),
                func.count(Booking.id).label("booking_count"),
                func.coalesce(func.sum(Service.precio_clp), 0).label("revenue"),
            )
            .select_from(Booking)
            .join(Service, Booking.service_id == Service.id)
            .where(Booking.estado.in_(["confirmed", "completed"]))
            .group_by(Service.id, Service.nombre, Service.categoria)
            .order_by(func.count(Booking.id).desc())
        )
        
        result = await self.session.execute(stmt)
        return [
            {
                "service_id": str(row.service_id),
                "service_name": row.service_name,
                "category": row.category,
                "booking_count": row.booking_count,
                "revenue": row.revenue or 0,
            }
            for row in result.all()
        ]

    async def get_revenue_stats(self, days: int = 30) -> dict:
        """Estadísticas de ingresos."""
        since = datetime.now().astimezone() - timedelta(days=days)
        
        # Total
        total = await self.session.scalar(
            select(func.coalesce(func.sum(Service.precio_clp), 0))
            .select_from(Booking)
            .join(Service, Booking.service_id == Service.id)
            .where(
                and_(
                    Booking.estado == "confirmed",
                    Booking.inicio >= since,
                )
            )
        ) or 0
        
        # Por día
        by_day = await self.get_bookings_by_day(days=days)
        
        # Por servicio
        by_service = await self.get_services_popularity()
        
        # Por profesional
        by_prof_stmt = (
            select(
                Professional.id.label("professional_id"),
                Professional.nombre.label("professional_name"),
                func.count(Booking.id).label("booking_count"),
                func.coalesce(func.sum(Service.precio_clp), 0).label("revenue"),
            )
            .select_from(Booking)
            .join(Service, Booking.service_id == Service.id)
            .join(Professional, Booking.professional_id == Professional.id)
            .where(
                and_(
                    Booking.estado == "confirmed",
                    Booking.inicio >= datetime.now().astimezone() - timedelta(days=days),
                )
            )
            .group_by(Professional.id, Professional.nombre)
            .order_by(func.count(Booking.id).desc())
        )
        
        prof_result = await self.session.execute(by_prof_stmt)
        by_professional = [
            {
                "professional_id": str(row.professional_id),
                "professional_name": row.professional_name,
                "booking_count": row.booking_count,
                "revenue": row.revenue or 0,
            }
            for row in prof_result.all()
        ]
        
        return {
            "total": total,
            "by_day": by_day,
            "by_service": by_service,
            "by_professional": by_professional,
        }