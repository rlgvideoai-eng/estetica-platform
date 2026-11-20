"""Service Service - Lógica de negocio para Servicios."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.service import Service, ServiceCategory
from ..schemas.service import ServiceCreate, ServiceUpdate, ServiceResponse


class ServiceService:
    """Lógica de negocio para Servicios."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_services(
        self,
        page: int = 1,
        size: int = 20,
        activo: bool = True,
    ) -> List[Service]:
        stmt = select(Service).where(Service.activo == activo).order_by(Service.nombre)
        stmt = stmt.offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_service(self, service_id: UUID) -> Optional[Service]:
        stmt = select(Service).where(Service.id == service_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_service(self, data) -> Service:
        service = Service(
            nombre=data.nombre,
            categoria=data.categoria,
            descripcion=data.descripcion,
            duracion_min=data.duracion_min,
            precio_clp=data.precio_clp,
            prep_limpieza_min=data.prep_limpieza_min,
            activo=data.activo,
        )
        self.session.add(service)
        await self.session.flush()
        await self.session.refresh(service)
        return service

    async def update_service(self, service_id: UUID, data) -> Optional[Service]:
        service = await self.get_service(service_id)
        if not service:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)

        await self.session.flush()
        await self.session.refresh(service)
        return service

    async def delete_service(self, service_id: UUID) -> bool:
        service = await self.get_service(service_id)
        if not service:
            return False

        # Soft delete - marcar como inactivo
        service.activo = False
        await self.session.flush()
        return True