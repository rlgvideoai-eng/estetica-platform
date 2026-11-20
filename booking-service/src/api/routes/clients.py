"""API Routes para Clientes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ...schemas.client import ClientCreate, ClientResponse
from ..deps import verify_internal_api_key
from ...services.client_service import ClientService
from ...db.session import get_session

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(verify_internal_api_key)])


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    session=Depends(get_session),
):
    """Crea un nuevo cliente."""
    client_service = ClientService(session)
    return await client_service.create_client(data)


@router.get("/by-telegram/{telegram_user_id}", response_model=ClientResponse)
async def get_client_by_telegram(
    telegram_user_id: int,
    session=Depends(get_session),
):
    """Obtiene cliente por telegram_user_id."""
    client_service = ClientService(session)
    client = await client_service.get_by_telegram_id(telegram_user_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    session=Depends(get_session),
):
    """Obtiene cliente por ID."""
    client_service = ClientService(session)
    client = await client_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client