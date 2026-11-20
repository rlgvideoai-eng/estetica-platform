"""Esquemas Pydantic para Service."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


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