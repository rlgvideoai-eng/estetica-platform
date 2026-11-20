"""API Routes para Reservas (Bookings)."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    BookingListResponse,
    BookingCreateResponse,
    AvailabilitySlot,
)
from ...schemas.client import ClientResponse
from ..deps import verify_internal_api_key
from ...services.booking_service import BookingService
from ...db.session import get_session

router = APIRouter(prefix="/bookings", tags=["bookings"], dependencies=[Depends(verify_internal_api_key)])


@router.post("", response_model=BookingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate,
    session=Depends(get_session),
):
    """Crea una nueva reserva (idempotente)."""
    booking_service = BookingService(session)
    result = await booking_service.create_booking(
        service_id=data.service_id,
        start_time=data.start_time,
        professional_id=data.professional_id,
        client=data.client.model_dump(),
        idempotency_key=data.idempotency_key,
    )
    return result


@router.get("", response_model=BookingListResponse)
async def list_bookings(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    client_id: Optional[UUID] = Query(None, description="Filtrar por cliente"),
    estado: Optional[str] = Query(None, pattern="^(pending|confirmed|cancelled|completed|no_show)$"),
    session=Depends(get_session),
):
    """Lista reservas con filtros y paginación."""
    booking_service = BookingService(session)
    items, total = await booking_service.list_bookings(
        page=page,
        size=size,
        client_id=client_id,
        estado=estado,
    )
    return BookingListResponse(items=items, total=total, page=page, size=size)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    session=Depends(get_session),
):
    """Obtiene una reserva por ID."""
    booking_service = BookingService(session)
    booking = await booking_service.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return booking


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: UUID,
    data: BookingUpdate,
    session=Depends(get_session),
):
    """Actualiza una reserva (reprogramar, cambiar estado, etc.)."""
    booking_service = BookingService(session)
    booking = await booking_service.update_booking(booking_id, data)
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: UUID,
    reason: Optional[str] = Query(None, description="Motivo de cancelación"),
    session=Depends(get_session),
):
    """Cancela una reserva (soft delete - estado cancelled)."""
    booking_service = BookingService(session)
    success = await booking_service.cancel_booking(booking_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Reserva no encontrada o no se puede cancelar")