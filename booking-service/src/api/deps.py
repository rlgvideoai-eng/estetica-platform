"""Dependencias de autenticación y autorización para API."""
from fastapi import Depends, Header, HTTPException, status

from ..config import settings


async def verify_internal_api_key(
    x_internal_api_key: str = Header(..., alias="X-Internal-Api-Key"),
) -> None:
    """Verifica la clave interna para comunicación entre servicios."""
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave API interna inválida",
        )


async def get_current_admin_user(
    # En producción, implementar JWT o session auth
    # Por ahora, mock
) -> dict:
    """Obtiene usuario admin autenticado (para panel admin futuro)."""
    return {"id": "admin", "role": "admin"}