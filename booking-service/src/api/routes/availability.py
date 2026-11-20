"""API Routes para Disponibilidad."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...schemas.availability import AvailabilityQuery, AvailabilityResponse, AvailabilitySlot
from ..deps import verify_internal_api_key
from ...services.availability_service import AvailabilityService
from ...db.session import get_session

router = APIRouter(prefix="/availability", tags=["availability"], dependencies=[Depends(verify_internal_api_key)])


@router.get("", response_model=AvailabilityResponse)
async def check_availability(
    service_id: UUID = Query(..., description="UUID del servicio"),
    from_date: datetime = Query(..., alias="from", description="Fecha inicio (ISO 8601)"),
    to_date: datetime = Query(..., alias="to", description="Fecha fin (ISO 8601)"),
    professional_id: UUID = Query(None, description="UUID profesional (opcional)"),
    session=Depends(get_session),
):
    """Consulta bloques horarios libres para un servicio en un rango de fechas."""
    if from_date >= to_date:
        raise HTTPException(status_code=400, detail="from_date debe ser anterior a to_date")

    # Validar horizonte máximo (configurable)
    from ...config import settings
    max_date = datetime.now().replace(tzinfo=None) + settings.booking_max_horizon_days
    if to_date > max_date:
        raise HTTPException(
            status_code=400,
            detail=f"Horizonte máximo: {settings.booking_max_horizon_days} días",
        )

    availability = AvailabilityService(session)
    slots = await availability.get_slots(
        service_id=service_id,
        from_date=from_date,
        to_date=to_date,
        professional_id=professional_id,
    )

    # Limitar a 9 slots para el teclado del bot
    return AvailabilityResponse(slots=slots[:9])