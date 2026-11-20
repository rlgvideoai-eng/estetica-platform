"""Esquemas Pydantic para Panel Administrativo."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================
# SERVICIOS
# ============================================================

class ServiceBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    categoria: str = Field(..., pattern="^(masaje|lavado|teñido|uñas|otro)$")
    descripcion: Optional[str] = None
    duracion_min: int = Field(..., gt=0, le=480)
    precio_clp: int = Field(..., ge=0, le=10000000)
    prep_limpieza_min: int = Field(default=0, ge=0, le=120)
    activo: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=120)
    categoria: Optional[str] = Field(None, pattern="^(masaje|lavado|teñido|uñas|otro)$")
    descripcion: Optional[str] = None
    duracion_min: Optional[int] = Field(None, gt=0, le=480)
    precio_clp: Optional[int] = Field(None, ge=0, le=10000000)
    prep_limpieza_min: Optional[int] = Field(None, ge=0, le=120)
    activo: Optional[bool] = None


class ServiceResponse(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================
# PROFESIONALES
# ============================================================

class ProfessionalBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    google_calendar_id: Optional[str] = None
    horario_semanal: dict = Field(default_factory=dict)
    activo: bool = True


class ProfessionalCreate(ProfessionalBase):
    service_ids: List[str] = Field(default_factory=list)


class ProfessionalUpdate(BaseModel):
    nombre: Optional[str] = None
    google_calendar_id: Optional[str] = None
    horario_semanal: Optional[dict] = None
    activo: Optional[bool] = None
    service_ids: Optional[List[str]] = None


class ProfessionalResponse(ProfessionalBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    service_ids: List[str] = Field(default_factory=list)


# ============================================================
# RESERVAS (ADMIN)
# ============================================================

class BookingAdminBase(BaseModel):
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


class BookingAdminResponse(BookingAdminBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class BookingAdminListResponse(BaseModel):
    items: List[BookingAdminResponse]
    total: int
    page: int
    size: int


# ============================================================
# ESTADÍSTICAS
# ============================================================

class AdminStats(BaseModel):
    total_bookings: int
    bookings_today: int
    bookings_this_week: int
    bookings_this_month: int
    pending_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    no_show_bookings: int
    total_revenue: int
    revenue_this_month: int
    active_clients: int
    active_professionals: int
    active_services: int
    occupancy_rate: float
    avg_rating: Optional[float] = None


# ============================================================
# ESTADÍSTICAS DETALLADAS
# ============================================================

class BookingByDay(BaseModel):
    date: str
    count: int
    revenue: int


class ServicePopularity(BaseModel):
    service_id: str
    service_name: str
    category: str
    booking_count: int
    revenue: int


class RevenueStats(BaseModel):
    total: int
    by_day: List[BookingByDay]
    by_service: List[ServicePopularity]
    by_professional: List[dict]