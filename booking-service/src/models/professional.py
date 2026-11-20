"""Modelos Professional y ProfessionalService (N:M)."""
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import BaseModel

if TYPE_CHECKING:
    from .service import Service
    from .booking import Booking


class Professional(BaseModel):
    """Profesional del centro."""
    __tablename__ = "professionals"

    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Horario semanal: { "mon": [{"start": "09:00", "end": "13:00"}, ...], ... }
    horario_semanal: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones
    services: Mapped[list["Service"]] = relationship(
        secondary="professional_services",
        back_populates="professionals",
        lazy="selectin",
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="professional",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Professional(id={self.id}, nombre='{self.nombre}')>"


class ProfessionalService(BaseModel):
    """Tabla intermedia N:M entre Professional y Service."""
    __tablename__ = "professional_services"
    __table_args__ = (
        UniqueConstraint("professional_id", "service_id", name="uq_professional_service"),
    )

    professional_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Para permitir prioridad/orden
    orden: Mapped[int] = mapped_column(default=0)

    def __repr__(self) -> str:
        return f"<ProfessionalService(prof_id={self.professional_id}, svc_id={self.service_id})>"