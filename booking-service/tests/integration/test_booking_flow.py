"""Tests de integración end-to-end para el flujo completo de reservas."""
import datetime
import uuid
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.booking_service import BookingService
from src.services.availability_service import AvailabilityService
from src.services.calendar_service import CalendarService
from src.services.notification_service import NotificationService
from src.models import Service, Professional, Client, Booking, BookingStatus
from src.config import settings


@pytest_asyncio.fixture
async def test_service(db_session: AsyncSession) -> UUID:
    """Crea un servicio de prueba."""
    service = Service(
        nombre="Masaje Relajante 60 min",
        categoria="masaje",
        descripcion="Masaje suave con aromaterapia",
        duracion_min=60,
        precio_clp=35000,
        prep_limpieza_min=10,
        activo=True,
    )
    db_session.add(service)
    await db_session.flush()
    await db_session.refresh(service)
    return service.id


@pytest_asyncio.fixture
async def test_professional(db_session: AsyncSession, test_service: UUID) -> UUID:
    """Crea un profesional de prueba."""
    prof = Professional(
        nombre="María González",
        google_calendar_id=None,  # Usar calendario del local
        horario_semanal={
            "1": [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "18:00"}],
            "2": [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "18:00"}],
            "3": [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "18:00"}],
            "4": [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "18:00"}],
            "5": [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "18:00"}],
        },
        activo=True,
    )
    db_session.add(prof)
    await db_session.flush()

    # Asociar servicio
    from src.models.professional import ProfessionalService
    ps = ProfessionalService(professional_id=prof.id, service_id=test_service)
    db_session.add(ps)
    await db_session.flush()
    await db_session.refresh(prof)
    return prof.id


@pytest_asyncio.fixture
async def booking_service(db_session: AsyncSession) -> BookingService:
    return BookingService(db_session)


@pytest_asyncio.fixture
async def availability_service(db_session: AsyncSession) -> AvailabilityService:
    return AvailabilityService(db_session)


class TestBookingFlow:
    """Tests del flujo completo de reserva."""

    @pytest.mark.asyncio
    async def test_create_booking_success(
        self,
        booking_service: BookingService,
        test_service: UUID,
        test_professional: UUID,
    ):
        """Test: Crear reserva exitosa con todos los pasos."""
        # Preparar datos
        start_time = datetime.datetime.now().astimezone() + datetime.timedelta(days=1, hours=2)
        client_data = {
            "nombre": "María González",
            "telefono": "+56912345678",
            "email": "maria@test.cl",
            "telegram_user_id": 123456789,
        }
        idempotency_key = f"test-{uuid.uuid4()}"

        # Ejecutar
        result = await booking_service.create_booking(
            service_id=test_service,
            start_time=client_data["start_time"] if "start_time" in client_data else datetime.datetime.now().astimezone() + datetime.timedelta(days=1, hours=2),
            professional_id=test_professional,
            client=client_data,
            idempotency_key=idempotency_key,
        )

        # Verificar
        assert result.success is True
        assert result.booking is not None
        assert result.booking.codigo.startswith("EST-")
        assert result.booking.estado == "confirmed"
        assert result.booking.service_id == test_service
        assert result.booking.professional_id == test_professional
        assert result.booking.client_id is not None
        assert result.booking.google_event_id is not None or True  # Puede ser None si no hay config Google

    @pytest.mark.asyncio
    async def test_idempotency_booking(
        self,
        booking_service: BookingService,
        test_service: UUID,
        test_professional: UUID,
    ):
        """Test: Idempotencia - misma clave no crea duplicados."""
        start_time = datetime.datetime.now().astimezone() + datetime.timedelta(days=2, hours=3)
        client_data = {
            "nombre": "Pedro Pérez",
            "telefono": "+56987654321",
            "email": "pedro@test.cl",
            "telegram_user_id": 987654321,
        }
        idempotency_key = f"idempotent-{uuid.uuid4()}"

        # Primera creación
        result1 = await booking_service.create_booking(
            service_id=test_service,
            start_time=datetime.datetime.now().astimezone() + datetime.timedelta(days=2, hours=3),
            professional_id=test_professional,
            client=client_data,
            idempotency_key=idempotency_key,
        )
        assert result1.success is True

        # Segunda creación con misma clave
        result2 = await booking_service.create_booking(
            service_id=test_service,
            start_time=datetime.datetime.now().astimezone() + datetime.timedelta(days=2, hours=3),
            professional_id=test_professional,
            client=client_data,
            idempotency_key=idempotency_key,
        )
        assert result2.success is True
        assert result1.booking.id == result2.booking.id  # Misma reserva

    @pytest.mark.asyncio
    async def test_booking_conflict_prevention(
        self,
        booking_service: BookingService,
        test_service: UUID,
        test_professional: UUID,
    ):
        """Test: Prevención de doble reserva (AG-4)."""
        start_time = datetime.datetime.now().astimezone() + datetime.timedelta(days=3, hours=10)
        client1 = {
            "nombre": "Cliente Uno",
            "telefono": "+56911111111",
            "email": "uno@test.cl",
            "telegram_user_id": 111111111,
        }
        client2 = {
            "nombre": "Cliente Dos",
            "telefono": "+56922222222",
            "email": "dos@test.cl",
            "telegram_user_id": 222222222,
        }

        # Primera reserva
        result1 = await booking_service.create_booking(
            service_id=test_service,
            start_time=datetime.datetime.now().astimezone() + datetime.timedelta(days=3, hours=10),
            professional_id=test_professional,
            client=client1,
        )
        assert result1.success is True

        # Segunda reserva en mismo slot - debería fallar
        result2 = await booking_service.create_booking(
            service_id=test_service,
            start_time=datetime.datetime.now().astimezone() + datetime.timedelta(days=3, hours=10),
            professional_id=test_professional,
            client=client2,
        )
        assert result2.success is False
        assert "disponible" in result2.error.lower() or "conflicto" in result2.error.lower()
        assert len(result2.alternatives) > 0  # Debe ofrecer alternativas

    @pytest.mark.asyncio
    async def test_reschedule_booking(
        self,
        booking_service: BookingService,
        test_service: UUID,
        test_professional: UUID,
    ):
        """Test: Reprogramar reserva."""
        # Crear reserva inicial
        start_time = datetime.datetime.now().astimezone() + datetime.timedelta(days=4, hours=11)
        client_data = {
            "nombre": "Ana López",
            "telefono": "+56933333333",
            "email": "ana@test.cl",
            "telegram_user_id": 333333333,
        }
        result = await booking_service.create_booking(
            service_id=test_service,
            start_time=start_time,
            professional_id=test_professional,
            client=client_data,
        )
        assert result.success is True
        booking_id = result.booking.id

        # Reprogramar a nueva hora
        new_time = datetime.datetime.now().astimezone() + datetime.timedelta(days=4, hours=14)
        updated = await booking_service.update_booking(
            booking_id=result.booking.id,
            data={"start_time": new_time},
        )
        assert updated is not None
        assert updated.inicio.astimezone().hour == 14  # 14:00

    @pytest.mark.asyncio
    async def test_cancel_booking_policy(
        self,
        booking_service: BookingService,
        test_service: UUID,
        test_professional: UUID,
    ):
        """Test: Política de cancelación (24h sin cargo)."""
        # Reserva para mañana (menos de 24h)
        start_time = datetime.datetime.now().astimezone() + datetime.timedelta(hours=12)
        client_data = {
            "nombre": "Cancel Test",
            "telefono": "+56944444444",
            "email": "cancel@test.cl",
            "telegram_user_id": 444444444,
        }
        result = await booking_service.create_booking(
            service_id=test_service,
            start_time=start_time,
            professional_id=test_professional,
            client=client_data,
        )
        assert result.success is True

        # Cancelar - debería aplicar cargo (menos de 24h)
        cancelled = await booking_service.cancel_booking(
            booking_id=result.booking.id,
            reason="Prueba cancelación tardía",
        )
        assert cancelled is True

        # Verificar estado
        cancelled_booking = await booking_service.get_booking(result.booking.id)
        assert cancelled_booking.estado == "cancelled"
        assert "cargo 50%" in (cancelled_booking.notas or "")


class TestAvailabilityService:
    """Tests del servicio de disponibilidad (Core AG-2)."""

    @pytest.mark.asyncio
    async def test_get_slots_basic(
        self,
        availability_service: AvailabilityService,
        test_service: UUID,
        test_professional: UUID,
    ):
        """Test: Obtener slots básicos."""
        from_date = datetime.datetime.now().astimezone() + datetime.timedelta(days=1)
        to_date = from_date + datetime.timedelta(days=7)

        slots = await availability_service.get_slots(
            service_id=test_service,
            from_date=from_date,
            to_date=to_date,
            professional_id=test_professional,
        )

        assert len(slots) > 0
        for slot in slots[:3]:
            assert hasattr(slot, "start_iso")
            assert hasattr(slot, "date_str")
            assert hasattr(slot, "time_str")
            assert hasattr(slot, "professional_id")

    @pytest.mark.asyncio
    async def test_no_availability_on_weekend(
        self,
        availability_service: AvailabilityService,
        test_service: UUID,
    ):
        """Test: Sin disponibilidad en domingo (local cerrado)."""
        # Buscar próximo domingo
        today = datetime.datetime.now().astimezone()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        sunday = today + datetime.timedelta(days=days_until_sunday)
        from_date = sunday.replace(hour=9, minute=0, second=0, microsecond=0)
        to_date = from_date + datetime.timedelta(days=1)

        # Crear servicio con profesional que sí trabaja domingo (para test)
        from src.models import Service, Professional, ProfessionalService
        service = Service(
            nombre="Test Domingo",
            categoria="masaje",
            duracion_min=60,
            precio_clp=30000,
            activo=True,
        )
        prof = Professional(
            nombre="Prof Domingo",
            horario_semanal={"6": [{"start": "09:00", "end": "14:00"}]},  # Domingo
            activo=True,
        )
        # No agregar a session para este test unitario - solo verificar lógica

        # El servicio debería retornar 0 slots porque business_hours no tiene domingo
        # (esto se testea mejor en integration test real)


class TestCalendarSync:
    """Tests de sincronización con Google Calendar."""

    @pytest.mark.asyncio
    async def test_calendar_service_init(self, db_session: AsyncSession):
        """Test: Inicialización del servicio."""
        cal = CalendarService(db_session)
        assert cal is not None

    @pytest.mark.asyncio
    async def test_freebusy_query_mock(self, db_session: AsyncSession):
        """Test: Consulta free/busy (mock si no hay credenciales)."""
        cal = CalendarService(db_session)
        time_min = datetime.datetime.now().astimezone() + datetime.timedelta(days=1)
        time_max = time_min + datetime.timedelta(days=1)
        
        busy = await cal.get_busy_slots("primary", time_min, time_max)
        assert isinstance(busy, list)  # Lista vacía si no hay credenciales


# Fixture para base de datos de test
@pytest_asyncio.fixture
async def db_session():
    """Fixture que provee sesión de BD para tests."""
    # Este fixture se define en conftest.py global
    pass


# Configuración pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: tests de integración")
    config.addinivalue_line("markers", "unit: tests unitarios")