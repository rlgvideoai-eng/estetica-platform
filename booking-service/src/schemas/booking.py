"""Esquemas Pydantic para Booking."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class ClientData(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    telefono: str = Field(..., min_length=8, max_length=30)
    email: EmailStr
    telegram_user_id: Optional[int] = None


class BookingCreate(BaseModel):
    service_id: UUID = Field(..., description="UUID del servicio")
    professional_id: Optional[UUID] = None
    start_time: datetime = Field(..., description="Inicio de la reserva (ISO 8601 UTC)")
    client: ClientData = Field(..., description="Datos del cliente")
    idempotency_key: Optional[str] = Field(default=None, max_length=64)


class BookingUpdate(BaseModel):
    estado: Optional[str] = Field(None, pattern="^(pending|confirmed|cancelled|completed|no_show)$")
    start_time: Optional[datetime] = None
    professional_id: Optional[str] = None
    notas: Optional[str] = None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo: str
    service_id: UUID
    professional_id: Optional[UUID] = None
    client_id: UUID
    inicio: datetime
    fin: datetime
    estado: str
    origen: str
    google_event_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    notas: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BookingListResponse(BaseModel):
    items: List["BookingResponse"]
    total: int
    page: int
    size: int


class BookingCreateResponse(BaseModel):
    success: bool
    booking: Optional["BookingResponse"] = None
    error: Optional[str] = None
    alternatives: List["AvailabilitySlot"] = []


# Forward references
BookingResponse.model_rebuild()