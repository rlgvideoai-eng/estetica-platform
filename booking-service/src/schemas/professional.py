"""Esquemas Pydantic para Professional."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfessionalBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    google_calendar_id: Optional[str] = None
    horario_semanal: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)
    activo: bool = True


class ProfessionalCreate(ProfessionalBase):
    service_ids: List[str] = Field(default_factory=list)


class ProfessionalUpdate(BaseModel):
    nombre: Optional[str] = None
    google_calendar_id: Optional[str] = None
    horario_semanal: Optional[Dict[str, List[Dict[str, str]]]] = None
    activo: Optional[bool] = None
    service_ids: Optional[List[str]] = None


class ProfessionalResponse(ProfessionalBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    service_ids: List[str] = Field(default_factory=list)