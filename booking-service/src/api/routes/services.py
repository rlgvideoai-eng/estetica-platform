"""API Routes para Servicios."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from ...schemas.client import ClientResponse
from ..deps import verify_internal_api_key
from ...services.service_service import ServiceService
from ...db.session import get_session

router = APIRouter(prefix="/services", tags=["services"], dependencies=[Depends(verify_internal_api_key)])


@router.get("", response_model=list[ServiceResponse])
async def list_services(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    activo: bool = Query(True, description="Filtrar solo activos"),
    session=Depends(get_session),
):
    """Lista servicios con paginación."""
    service = ServiceService(session)
    items = await service.list_services(page=page, size=size, activo=activo)
    return items


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    session=Depends(get_session),
):
    """Obtiene un servicio por ID."""
    service = ServiceService(session)
    svc = await service.get_service(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return svc


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    session=Depends(get_session),
):
    """Crea un nuevo servicio."""
    service = ServiceService(session)
    return await service.create_service(data)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    data: ServiceUpdate,
    session=Depends(get_session),
):
    """Actualiza un servicio."""
    service = ServiceService(session)
    svc = await service.update_service(service_id, data)
    if not svc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return svc


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: UUID,
    session=Depends(get_session),
):
    """Elimina (soft delete) un servicio."""
    service = ServiceService(session)
    await service.delete_service(service_id)