"""Esquemas Pydantic para tool calling del agente."""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ============================================================
# INPUTS DE HERRAMIENTAS
# ============================================================

class SearchKnowledgeInput(BaseModel):
    query: str = Field(..., description="Pregunta del usuario en lenguaje natural")
    top_k: int = Field(default=4, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class ListServicesInput(BaseModel):
    """Sin parámetros - lista todos los servicios activos."""
    pass


class CheckAvailabilityInput(BaseModel):
    service_id: str = Field(..., description="UUID del servicio")
    from_date: datetime = Field(..., description="Fecha inicio rango (ISO 8601)")
    to_date: datetime = Field(..., description="Fecha fin rango (ISO 8601)")
    professional_id: Optional[str] = Field(default=None, description="UUID profesional (opcional)")


class CreateBookingInput(BaseModel):
    service_id: str = Field(..., description="UUID del servicio")
    start_time: datetime = Field(..., description="Inicio de la reserva (ISO 8601, UTC)")
    professional_id: Optional[str] = Field(default=None, description="UUID profesional (opcional)")
    client: Dict[str, Any] = Field(..., description="Datos del cliente: nombre, telefono, email, telegram_user_id")
    idempotency_key: Optional[str] = Field(default=None, description="Clave única para evitar duplicados")


class GetBookingInput(BaseModel):
    booking_id: Optional[str] = Field(default=None, description="UUID de la reserva")
    client_telegram_id: Optional[int] = Field(default=None, description="Telegram user ID del cliente")


class RescheduleBookingInput(BaseModel):
    booking_id: str = Field(..., description="UUID de la reserva")
    new_start_time: datetime = Field(..., description="Nuevo inicio (ISO 8601, UTC)")


class CancelBookingInput(BaseModel):
    booking_id: str = Field(..., description="UUID de la reserva")
    reason: Optional[str] = Field(default=None, description="Motivo de cancelación")


class HandoffToHumanInput(BaseModel):
    summary: str = Field(..., description="Resumen de la conversación para la administradora")
    telegram_user_id: int = Field(..., description="ID de Telegram del usuario")
    username: Optional[str] = None
    first_name: Optional[str] = None


# ============================================================
# OUTPUTS DE HERRAMIENTAS
# ============================================================

class RAGChunk(BaseModel):
    text: str
    source: str
    score: float


class SearchKnowledgeOutput(BaseModel):
    chunks: List[RAGChunk] = Field(default_factory=list)


class ServiceInfo(BaseModel):
    id: str
    nombre: str
    categoria: str
    descripcion: Optional[str] = None
    duracion_min: int
    precio_clp: int
    prep_limpieza_min: int = 0


class ListServicesOutput(BaseModel):
    services: List[ServiceInfo] = Field(default_factory=list)


class AvailabilitySlot(BaseModel):
    start_iso: str = Field(..., description="ISO 8601 UTC")
    end_iso: str
    date_str: str = Field(..., description="DD/MM/YYYY")
    time_str: str = Field(..., description="HH:MM")
    professional_id: Optional[str] = None
    professional_name: Optional[str] = None


class CheckAvailabilityOutput(BaseModel):
    slots: List[AvailabilitySlot] = Field(default_factory=list)


class BookingInfo(BaseModel):
    id: str
    codigo: str
    service_id: str
    service_name: str
    professional_id: Optional[str] = None
    professional_name: Optional[str] = None
    inicio: str  # ISO 8601 UTC
    fin: str
    estado: str
    precio: int


class CreateBookingOutput(BaseModel):
    success: bool
    booking: Optional[BookingInfo] = None
    error: Optional[str] = None
    alternatives: List[AvailabilitySlot] = Field(default_factory=list)


class GetBookingOutput(BaseModel):
    bookings: List[BookingInfo] = Field(default_factory=list)


class RescheduleBookingOutput(BaseModel):
    success: bool
    booking: Optional[BookingInfo] = None
    error: Optional[str] = None


class CancelBookingOutput(BaseModel):
    success: bool
    booking: Optional[BookingInfo] = None
    error: Optional[str] = None


class HandoffToHumanOutput(BaseModel):
    success: bool
    message: str


# ============================================================
# AGENT RESPONSE
# ============================================================

class AgentMessage(BaseModel):
    type: Literal["text", "voice"]
    content: str = ""  # para text
    audio_bytes: Optional[bytes] = None  # para voice
    caption: Optional[str] = None
    keyboard: Optional[Any] = None


class AgentResponse(BaseModel):
    messages: List[AgentMessage] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    should_handoff: bool = False
    handoff_summary: Optional[str] = None