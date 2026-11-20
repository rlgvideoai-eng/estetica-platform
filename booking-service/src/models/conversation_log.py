"""Modelo ConversationLog - Log de conversaciones del bot."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import BaseModel

if TYPE_CHECKING:
    pass


class ConversationLog(BaseModel):
    """Log de conversaciones para auditoría y análisis."""
    __tablename__ = "conversation_logs"

    canal: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # telegram, whatsapp, voice
    usuario_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # telegram_user_id, phone, etc.
    mensajes_resumen: Mapped[dict] = mapped_column(JSONB, nullable=False)  # últimos N mensajes estructurados
    resultado: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # booked, info, handoff, error
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now().astimezone(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<ConversationLog(canal={self.canal}, user={self.usuario_id}, resultado={self.resultado})>"