"""Base declarativa y mixins para modelos SQLAlchemy 2.0."""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, func, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos."""
    pass


class TimestampMixin:
    """Mixin para campos created_at y updated_at automáticos."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin para PK UUID automático."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class SoftDeleteMixin:
    """Mixin para soft delete (opcional)."""
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Modelo base con UUID + timestamps."""
    __abstract__ = True