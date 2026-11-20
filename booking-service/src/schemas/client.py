"""Esquemas Pydantic para Client."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    telefono: str = Field(..., min_length=8, max_length=30)
    email: EmailStr
    telegram_user_id: Optional[int] = Field(default=None, ge=1)
    consentimiento: bool = False


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    telefono: str
    email: EmailStr
    telegram_user_id: Optional[int] = None
    consentimiento: bool
    fecha_alta: datetime
    created_at: datetime
    updated_at: datetime