"""Modelo Client - Clientes del centro."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import BaseModel

if TYPE_CHECKING:
    from .booking import Booking


class Client(BaseModel):
    """Cliente del centro."""
    __tablename__ = "clients"

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True, index=True)
    consentimiento: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_alta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relaciones
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="client",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, nombre='{self.nombre}', email='{self.email}')>"