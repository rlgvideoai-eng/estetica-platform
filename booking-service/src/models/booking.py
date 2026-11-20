"""Modelo Booking - Reservas."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import BaseModel

if TYPE_CHECKING:
    from .client import Client
    from .service import Service
    from .professional import Professional


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Booking(BaseModel):
    """Reserva de un cliente."""
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_booking_idempotency"),
        CheckConstraint("fin > inicio", name="ck_booking_fin_post_inicio"),
        Index("ix_bookings_client_inicio", "client_id", "inicio"),
        Index("ix_bookings_prof_inicio", "professional_id", "inicio"),
        Index("ix_bookings_estado", "estado"),
    )

    # Código legible: EST-YYYYMMDD-XXX
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    professional_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("professionals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    fin: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    estado: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status", native_enum=False),
        nullable=False,
        default=BookingStatus.PENDING,
    )

    origen: Mapped[str] = mapped_column(String(50), nullable=False, default="telegram")
    google_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Clave de idempotencia para evitar duplicados
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)

    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relaciones
    client: Mapped["Client"] = relationship(back_populates="bookings", lazy="selectin")
    service: Mapped["Service"] = relationship(lazy="selectin")
    professional: Mapped[Optional["Professional"]] = relationship(back_populates="bookings", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Booking(codigo='{self.codigo}', estado={self.estado}, inicio={self.inicio})>"