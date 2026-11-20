"""API Routes para Panel Administrativo."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...schemas.admin import (
    AdminStats,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
    ProfessionalCreate,
    ProfessionalResponse,
    ProfessionalUpdate,
    BookingAdminResponse,
    BookingAdminListResponse,
)
from ..deps import verify_internal_api_key
from ...services.admin_service import AdminService
from ...db.session import get_session

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_internal_api_key)])


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(session=Depends(get_session)):
    """Obtiene estadísticas generales para el dashboard."""
    admin_service = AdminService(session)
    return await admin_service.get_stats()


# ============================================================
# SERVICIOS
# ============================================================

@router.get("/services", response_model=List[ServiceResponse])
async def list_services_admin(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    activo: Optional[bool] = None,
    session=Depends(get_session),
):
    """Lista servicios con paginación (admin)."""
    from ...services.service_service import ServiceService
    service = ServiceService(session)
    return await service.list_services(page=page, size=size, activo=activo)


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service_admin(service_id: UUID, session=Depends(get_session)):
    """Obtiene un servicio por ID."""
    from ...services.service_service import ServiceService
    service = ServiceService(session)
    svc = await service.get_service(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return svc


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service_admin(data: ServiceCreate, session=Depends(get_session)):
    """Crea un nuevo servicio."""
    from ...services.service_service import ServiceService
    service = ServiceService(session)
    return await service.create_service(data)


@router.patch("/services/{service_id}", response_model=ServiceResponse)
async def update_service_admin(service_id: UUID, data: ServiceUpdate, session=Depends(get_session)):
    """Actualiza un servicio."""
    from ...services.service_service import ServiceService
    service = ServiceService(session)
    svc = await service.update_service(service_id, data)
    if not svc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return svc


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_admin(service_id: UUID, session=Depends(get_session)):
    """Elimina (soft delete) un servicio."""
    from ...services.service_service import ServiceService
    service = ServiceService(session)
    await service.delete_service(service_id)


# ============================================================
# PROFESIONALES
# ============================================================

@router.get("/professionals", response_model=List[ProfessionalResponse])
async def list_professionals_admin(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    activo: Optional[bool] = None,
    session=Depends(get_session),
):
    """Lista profesionales con paginación (admin)."""
    from ...services.professional_service import ProfessionalService
    service = ProfessionalService(session)
    return await service.list_professionals(page=page, size=size, activo=activo)


@router.get("/professionals/{professional_id}", response_model=ProfessionalResponse)
async def get_professional_admin(professional_id: UUID, session=Depends(get_session)):
    """Obtiene un profesional por ID."""
    from ...services.professional_service import ProfessionalService
    service = ProfessionalService(session)
    prof = await service.get_professional(professional_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    return prof


@router.post("/professionals", response_model=ProfessionalResponse, status_code=status.HTTP_201_CREATED)
async def create_professional_admin(data: ProfessionalCreate, session=Depends(get_session)):
    """Crea un nuevo profesional."""
    from ...services.professional_service import ProfessionalService
    service = ProfessionalService(session)
    return await service.create_professional(data)


@router.patch("/professionals/{professional_id}", response_model=ProfessionalResponse)
async def update_professional_admin(professional_id: UUID, data: ProfessionalUpdate, session=Depends(get_session)):
    """Actualiza un profesional."""
    from ...services.professional_service import ProfessionalService
    service = ProfessionalService(session)
    prof = await service.update_professional(professional_id, data)
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    return prof


@router.delete("/professionals/{professional_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_professional_admin(professional_id: UUID, session=Depends(get_session)):
    """Elimina (soft delete) un profesional."""
    from ...services.professional_service import ProfessionalService
    service = ProfessionalService(session)
    await service.delete_professional(professional_id)


# ============================================================
# RESERVAS (ADMIN)
# ============================================================

@router.get("/bookings", response_model=BookingAdminListResponse)
async def list_bookings_admin(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    client_id: Optional[UUID] = Query(None),
    estado: Optional[str] = Query(None, pattern="^(pending|confirmed|cancelled|completed|no_show)$"),
    session=Depends(get_session),
):
    """Lista reservas con filtros (admin)."""
    from ...services.booking_service import BookingService
    service = BookingService(session)
    items, total = await service.list_bookings(page=page, size=size, client_id=None, estado=estado)
    from ...schemas.booking import BookingAdminListResponse
    return BookingAdminListResponse(items=items, total=total, page=page, size=size)


@router.get("/bookings/{booking_id}", response_model=BookingAdminResponse)
async def get_booking_admin(booking_id: UUID, session=Depends(get_session)):
    """Obtiene una reserva por ID."""
    from ...services.booking_service import BookingService
    service = BookingService(session)
    booking = await service.get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return booking


@router.patch("/bookings/{booking_id}", response_model=BookingAdminResponse)
async def update_booking_admin(booking_id: UUID, data: dict, session=Depends(get_session)):
    """Actualiza una reserva (reprogramar, cancelar, cambiar estado)."""
    from ...services.booking_service import BookingService
    from ...schemas.booking import BookingUpdate
    
    service = BookingService(session)
    update_data = BookingUpdate(**data)
    booking = await service.update_booking(booking_id, update_data)
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return booking


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking_admin(booking_id: UUID, reason: Optional[str] = None, session=Depends(get_session)):
    """Cancela una reserva (admin)."""
    from ...services.booking_service import BookingService
    service = BookingService(session)
    success = await service.cancel_booking(booking_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Reserva no encontrada o no se puede cancelar")


# ============================================================
# ESTADÍSTICAS
# ============================================================

@router.get("/stats", response_model=dict)
async def get_dashboard_stats(session=Depends(get_session)):
    """Estadísticas para dashboard administrativo."""
    from ...services.admin_service import AdminService
    admin = AdminService(session)
    return await admin.get_stats()


@router.get("/stats/bookings-by-day")
async def get_bookings_by_day(
    days: int = Query(30, ge=1, le=90),
    session=Depends(get_session),
):
    """Reservas por día para gráficos."""
    from ...services.admin_service import AdminService
    admin = AdminService(session)
    return await admin.get_bookings_by_day(days)


@router.get("/stats/services-popularity")
async def get_services_popularity(session=Depends(get_session)):
    """Popularidad de servicios."""
    from ...services.admin_service import AdminService
    admin = AdminService(session)
    return await admin.get_services_popularity()


@router.get("/stats/revenue")
async def get_revenue_stats(
    days: int = Query(30, ge=1, le=365),
    session=Depends(get_session),
):
    """Estadísticas de ingresos."""
    from ...services.admin_service import AdminService
    admin = AdminService(session)
    return await admin.get_revenue_stats(days)