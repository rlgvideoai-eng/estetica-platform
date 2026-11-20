"""Cliente HTTP para booking-service."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings
from ..utils import get_logger
from ..agent.schemas import (
    ServiceInfo,
    AvailabilitySlot,
    BookingInfo,
    CreateBookingOutput,
    GetBookingOutput,
    RescheduleBookingOutput,
    CancelBookingOutput,
)

logger = get_logger(__name__)

# Cliente HTTP compartido
_http_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            base_url=settings.booking_service_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={
                "Content-Type": "application/json",
                "X-Internal-Api-Key": settings.internal_api_key,
            },
        )
    return _http_client


async def close_client() -> None:
    """Cierra el cliente HTTP (para shutdown)."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


# ============================================================
# SERVICIOS
# ============================================================

async def list_services() -> List[ServiceInfo]:
    """Obtiene lista de servicios activos."""
    client = _get_client()
    try:
        response = await client.get("/services")
        response.raise_for_status()
        data = response.json()
        return [ServiceInfo(**item) for item in data.get("items", [])]
    except Exception as e:
        logger.exception("list_services_error", error=str(e))
        # Fallback mock
        return _mock_services()


async def get_service(service_id: str) -> Optional[ServiceInfo]:
    """Obtiene un servicio por ID."""
    client = _get_client()
    try:
        response = await client.get(f"/services/{service_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return ServiceInfo(**response.json())
    except Exception as e:
        logger.exception("get_service_error", service_id=service_id, error=str(e))
        return None


async def get_professionals_for_service(service_id: str) -> List[Dict]:
    """Obtiene profesionales que realizan un servicio."""
    client = _get_client()
    try:
        response = await client.get(f"/services/{service_id}/professionals")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.exception("get_professionals_error", service_id=service_id, error=str(e))
        return []


# ============================================================
# DISPONIBILIDAD
# ============================================================

async def check_availability(
    service_id: str,
    from_date: datetime,
    to_date: datetime,
    professional_id: Optional[str] = None,
) -> List[AvailabilitySlot]:
    """Consulta bloques horarios libres."""
    client = _get_client()
    params = {
        "service_id": service_id,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
    }
    if professional_id:
        params["professional_id"] = professional_id

    try:
        response = await client.get("/availability", params=params)
        response.raise_for_status()
        slots_data = response.json()
        return [AvailabilitySlot(**slot) for slot in slots_data]
    except Exception as e:
        logger.exception("check_availability_error", error=str(e))
        # Fallback mock
        return _mock_availability(service_id, professional_id)


# ============================================================
# RESERVAS
# ============================================================

async def create_booking(
    service_id: str,
    start_time: str,  # ISO 8601
    professional_id: Optional[str],
    client: Dict[str, Any],
    idempotency_key: str,
) -> CreateBookingOutput:
    """Crea una reserva."""
    client = _get_client()
    payload = {
        "service_id": service_id,
        "start_time": start_time,
        "professional_id": professional_id,
        "client": client,
        "idempotency_key": idempotency_key,
    }

    try:
        response = await client.post("/bookings", json=payload)
        if response.status_code == 201:
            return CreateBookingOutput(**response.json())
        elif response.status_code == 409:
            # Conflicto - devolver alternativas
            data = response.json()
            return CreateBookingOutput(
                success=False,
                error=data.get("error", "Horario no disponible"),
                alternatives=[AvailabilitySlot(**alt) for alt in data.get("alternatives", [])],
            )
        else:
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.exception("create_booking_http_error", status=e.response.status_code, error=e.response.text)
        return CreateBookingOutput(success=False, error=f"Error HTTP: {e.response.status_code}")
    except Exception as e:
        logger.exception("create_booking_error", error=str(e))
        return CreateBookingOutput(success=False, error="Error de conexión con servicio de reservas")

    return CreateBookingOutput(success=False, error="Error desconocido")


async def get_booking(
    booking_id: Optional[str] = None,
    client_telegram_id: Optional[int] = None,
) -> GetBookingOutput:
    """Obtiene reserva(s) por ID o por cliente."""
    client = _get_client()
    params = {}
    if booking_id:
        params["booking_id"] = booking_id
    if client_telegram_id:
        params["client_telegram_id"] = client_telegram_id

    try:
        response = await client.get("/bookings", params=params)
        response.raise_for_status()
        data = response.json()
        bookings = [BookingInfo(**b) for b in data.get("items", [])]
        return GetBookingOutput(bookings=bookings)
    except Exception as e:
        logger.exception("get_booking_error", error=str(e))
        return GetBookingOutput(bookings=[])


async def reschedule_booking(
    booking_id: str,
    new_start_time: str,
) -> RescheduleBookingOutput:
    """Reprograma una reserva."""
    client = _get_client()
    payload = {"new_start_time": new_start_time}

    try:
        response = await client.patch(f"/bookings/{booking_id}", json=payload)
        if response.status_code == 200:
            return RescheduleBookingOutput(**response.json())
        elif response.status_code == 409:
            data = response.json()
            return RescheduleBookingOutput(
                success=False,
                error=data.get("error", "Horario no disponible"),
            )
        else:
            response.raise_for_status()
    except Exception as e:
        logger.exception("reschedule_booking_error", error=str(e))
        return RescheduleBookingOutput(success=False, error="Error de conexión")

    return RescheduleBookingOutput(success=False, error="Error desconocido")


async def cancel_booking(
    booking_id: str,
    reason: Optional[str] = None,
) -> CancelBookingOutput:
    """Cancela una reserva."""
    client = _get_client()
    params = {"reason": reason} if reason else {}

    try:
        response = await client.delete(f"/bookings/{booking_id}", params=params)
        if response.status_code == 204:
            return CancelBookingOutput(success=True, booking=None)
        elif response.status_code == 409:
            data = response.json()
            return CancelBookingOutput(success=False, error=data.get("error", "No se puede cancelar"))
        else:
            response.raise_for_status()
    except Exception as e:
        logger.exception("cancel_booking_error", error=str(e))
        return CancelBookingOutput(success=False, error="Error de conexión")

    return CancelBookingOutput(success=False, error="Error desconocido")


async def get_client_by_telegram(telegram_user_id: int) -> Optional[Dict]:
    """Obtiene cliente por telegram_user_id."""
    client = _get_client()
    try:
        response = await client.get(f"/clients/by-telegram/{telegram_user_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.exception("get_client_by_telegram_error", error=str(e))
        return None


# ============================================================
# MOCKS PARA DESARROLLO (Fase 0-2)
# ============================================================

def _mock_services() -> List[ServiceInfo]:
    """Servicios mock para desarrollo."""
    return [
        ServiceInfo(
            id="11111111-1111-1111-1111-111111111111",
            nombre="Masaje Relajante 60 min",
            categoria="masaje",
            descripcion="Masaje suave con aromaterapia para relajación profunda",
            duracion_min=60,
            precio_clp=35000,
            prep_limpieza_min=10,
        ),
        ServiceInfo(
            id="22222222-2222-2222-2222-222222222222",
            nombre="Masaje Descontracturante 60 min",
            categoria="masaje",
            descripcion="Presión profunda para liberar contracturas musculares",
            duracion_min=60,
            precio_clp=40000,
            prep_limpieza_min=10,
        ),
        ServiceInfo(
            id="33333333-3333-3333-3333-333333333333",
            nombre="Lavado + Hidratación 45 min",
            categoria="lavado",
            descripcion="Lavado profundo con mascarilla hidratante",
            duracion_min=45,
            precio_clp=25000,
            prep_limpieza_min=5,
        ),
        ServiceInfo(
            id="44444444-4444-4444-4444-444444444444",
            nombre="Color Completo 90 min",
            categoria="teñido",
            descripcion="Coloración total con productos profesionales",
            duracion_min=90,
            precio_clp=45000,
            prep_limpieza_min=15,
        ),
        ServiceInfo(
            id="55555555-5555-5555-5555-555555555555",
            nombre="Esmaltado Semipermanente 45 min",
            categoria="uñas",
            descripcion="Esmaltado gel duradero 2-3 semanas",
            duracion_min=45,
            precio_clp=25000,
            prep_limpieza_min=5,
        ),
    ]


def _mock_availability(service_id: str, professional_id: Optional[str]) -> List[AvailabilitySlot]:
    """Disponibilidad mock para desarrollo."""
    from datetime import datetime, timedelta, time
    import pytz

    santiago = pytz.timezone("America/Santiago")
    slots = []
    base_date = datetime.now().date()

    for day_offset in range(14):
        current_date = base_date + timedelta(days=day_offset)
        # Solo días hábiles
        if current_date.weekday() >= 5:
            continue

        # 3 slots por día: mañana, mediodía, tarde
        for hour in [10, 13, 16]:
            start_naive = datetime.combine(current_date, time(hour, 0))
            start = santiago.localize(start_naive)
            end = start + timedelta(minutes=60)

            slots.append(AvailabilitySlot(
                start_iso=start.isoformat(),
                end_iso=end.isoformat(),
                date_str=start.strftime("%d/%m/%Y"),
                time_str=start.strftime("%H:%M"),
                professional_id=professional_id or "prof-mock-1",
                professional_name="María González",
            ))

    return slots[:9]  # Máximo 9 para el teclado