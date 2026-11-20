"""Esquemas Pydantic para Availability."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AvailabilityQuery(BaseModel):
    service_id: UUID = Field(..., description="UUID del servicio")
    from_date: datetime = Field(..., description="Fecha inicio rango (ISO 8601)", alias="from")
    to_date: datetime = Field(..., description="Fecha fin rango (ISO 8601)", alias="to")
    professional_id: Optional[UUID] = Field(default=None, description="UUID profesional (opcional)")

    model_config = ConfigDict(populate_by_name=True)


class AvailabilitySlot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_iso: str = Field(..., description="ISO 8601 UTC")
    end_iso: str
    date_str: str = Field(..., description="DD/MM/YYYY")
    time_str: str = Field(..., description="HH:MM")
    professional_id: Optional[UUID] = None
    professional_name: Optional[str] = None


class AvailabilityResponse(BaseModel):
    slots: List[AvailabilitySlot] = Field(default_factory=list)