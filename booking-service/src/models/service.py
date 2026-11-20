"""Modelo Service - Servicios ofrecidos."""
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String, Text, Boolean, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import BaseModel

if TYPE_CHECKING:
    from .professional import Professional, ProfessionalService


class ServiceCategory(str, enum.Enum):
    MASAJE = "masaje"
    LAVADO = "lavado"
    TEÑIDO = "teñido"
    UÑAS = "uñas"
    OTRO = "otro"


class Service(BaseModel):
    """Servicio ofrecido por el centro."""
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("duracion_min > 0", name="ck_service_duracion_positiva"),
        CheckConstraint("precio_clp >= 0", name="ck_service_precio_no_negativo"),
        CheckConstraint("prep_limpieza_min >= 0", name="ck_service_prep_no_negativo"),
    )

    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    categoria: Mapped[ServiceCategory] = mapped_column(
        Enum(ServiceCategory, name="service_category", native_enum=False),
        nullable=False,
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duracion_min: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    prep_limpieza_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones
    professionals: Mapped[list["Professional"]] = relationship(
        secondary="professional_services",
        back_populates="services",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, nombre='{self.nombre}', precio={self.precio_clp})>"