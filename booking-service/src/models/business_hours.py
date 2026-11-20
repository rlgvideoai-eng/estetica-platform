"""Modelo BusinessHours - Horarios del local."""
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import BaseModel

if TYPE_CHECKING:
    from .time_block import TimeBlock


class BusinessHours(BaseModel):
    """Horarios de atención del local."""
    __tablename__ = "business_hours"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_bh_dia_semana"),
    )

    # 0=Domingo, 1=Lunes, ..., 6=Sábado
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # Tramos: [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "19:00"}]
    tramos: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Excepciones: [{"date": "2024-12-25", "razon": "Navidad"}, ...]
    excepciones: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    activo: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        dias = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
        return f"<BusinessHours(dia={dias[self.dia_semana]}, tramos={len(self.tramos)})>"