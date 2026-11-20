"""Client Service - Lógica de negocio para Clientes."""
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.client import Client
from ..schemas.client import ClientCreate, ClientResponse


class ClientService:
    """Lógica de negocio para Clientes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_client(self, data: ClientCreate) -> Client:
        """Crea un nuevo cliente."""
        client = Client(
            nombre=data.nombre,
            telefono=data.telefono,
            email=data.email,
            telegram_user_id=data.telegram_user_id,
            consentimiento=data.consentimiento,
            fecha_alta=datetime.datetime.now().astimezone(),
        )
        self.session.add(client)
        await self.session.flush()
        await self.session.refresh(client)
        return client

    async def get_client(self, client_id: UUID) -> Optional[Client]:
        stmt = select(Client).where(Client.id == client_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_user_id: int) -> Optional[Client]:
        stmt = select(Client).where(Client.telegram_user_id == telegram_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()