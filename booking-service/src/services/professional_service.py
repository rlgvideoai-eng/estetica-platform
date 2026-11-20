"""Professional Service - Lógica de negocio para Profesionales."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.professional import Professional, ProfessionalService
from ..models.service import Service
from ..schemas.professional import ProfessionalCreate, ProfessionalUpdate, ProfessionalResponse


class ProfessionalService:
    """Lógica de negocio para Profesionales."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_professionals(
        self,
        page: int = 1,
        size: int = 20,
        activo: bool = True,
    ) -> List[Professional]:
        stmt = select(Professional).where(Professional.activo == activo).order_by(Professional.nombre)
        stmt = stmt.offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_professional(self, professional_id: UUID) -> Optional[Professional]:
        stmt = select(Professional).where(Professional.id == professional_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_professional(self, data: ProfessionalCreate) -> Professional:
        professional = Professional(
            nombre=data.nombre,
            google_calendar_id=data.google_calendar_id,
            horario_semanal=data.horario_semanal,
            activo=data.activo,
        )
        self.session.add(professional)
        await self.session.flush()

        # Asociar servicios
        if data.service_ids:
            for svc_id in data.service_ids:
                from ..models.professional import ProfessionalService as PS
                ps = PS(professional_id=professional.id, service_id=svc_id)
                self.session.add(ps)

        await self.session.flush()
        await self.session.refresh(professional)
        return professional

    async def update_professional(self, professional_id: UUID, data: ProfessionalUpdate) -> Optional[Professional]:
        professional = await self.get_professional(professional_id)
        if not professional:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude={"service_ids"})
        for field, value in update_data.items():
            setattr(professional, field, value)

        # Actualizar servicios si se proporcionan
        if data.service_ids is not None:
            # Eliminar asociaciones existentes
            await self.session.execute(
                ProfessionalService.__table__.delete().where(ProfessionalService.professional_id == professional_id)
            )
            # Crear nuevas
            for svc_id in data.service_ids:
                ps = ProfessionalService(professional_id=professional_id, service_id=svc_id)
                self.session.add(ps)

        await self.session.flush()
        await self.session.refresh(professional)
        return professional

    async def delete_professional(self, professional_id: UUID) -> bool:
        professional = await self.get_professional(professional_id)
        if not professional:
            return False

        professional.activo = False
        await self.session.flush()
        return True

    async def get_professionals_for_service(self, service_id: UUID) -> List[Professional]:
        stmt = (
            select(Professional)
            .join(ProfessionalService, Professional.id == ProfessionalService.professional_id)
            .where(
                ProfessionalService.service_id == service_id,
                Professional.activo == True,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())