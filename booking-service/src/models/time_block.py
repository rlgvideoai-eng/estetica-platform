"""Modelo TimeBlock - Bloqueos manuales de horario."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import BaseModel

if TYPE_CHECKING:
    from .professional import Professional


class TimeBlock(BaseModel):
    """Bloqueo manual de horario (profesional o local)."""
    __tablename__ = "time_blocks"

    # NULL = bloqueo del local completo; profesional_id = bloqueo de esa profesional
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
    motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relaciones
    professional: Mapped[Optional["Professional"]] = relationship(
        back_populates="time_blocks",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        scope = f"prof={self.professional_id}" if self.professional_id else "local"
        return f"<TimeBlock({scope}, {self.inicio} - {self.fin})>"