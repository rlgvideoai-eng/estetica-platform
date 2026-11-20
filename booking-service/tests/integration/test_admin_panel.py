"""Tests de integración para Panel Administrativo."""
import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app
from src.config import settings


@pytest_asyncio.fixture
async def admin_client():
    """Cliente HTTP para tests del panel admin."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Agregar header de autenticación interna
        client.headers["X-Internal-Api-Key"] = settings.internal_api_key
        yield client


@pytest_asyncio.fixture
async def db_session():
    """Fixture que provee sesión de BD para tests."""
    from src.db.session import get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


class TestAdminPanel:
    """Tests para el Panel Administrativo."""

    @pytest.mark.asyncio
    async def test_admin_stats(self, admin_client: AsyncClient):
        """Test: Obtener estadísticas del dashboard."""
        response = await admin_client.get("/admin/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "total_bookings" in data
        assert "bookings_today" in data
        assert "bookings_this_week" in data
        assert "bookings_this_month" in data
        assert "pending_bookings" in data
        assert "confirmed_bookings" in data
        assert "cancelled_bookings" in data
        assert "no_show_bookings" in data
        assert "total_revenue" in data
        assert "revenue_this_month" in data
        assert "active_clients" in data
        assert "active_professionals" in data
        assert "active_services" in data
        assert "occupancy_rate" in data

    @pytest.mark.asyncio
    async def test_admin_services_crud(self, admin_client: AsyncClient, db_session):
        """Test: CRUD completo de servicios."""
        # Crear servicio
        service_data = {
            "nombre": "Test Masaje",
            "categoria": "masaje",
            "descripcion": "Masaje de prueba",
            "duracion_min": 60,
            "precio_clp": 35000,
            "prep_limpieza_min": 10,
            "activo": True,
        }
        
        # Crear
        response = await admin_client.post("/admin/services", json=service_data)
        assert response.status_code == 201
        created = response.json()
        assert created["nombre"] == "Test Masaje"
        assert created["categoria"] == "masaje"
        assert created["precio_clp"] == 35000
        service_id = created["id"]
        
        # Leer
        response = await admin_client.get(f"/admin/services/{service_id}")
        assert response.status_code == 200
        service = response.json()
        assert service["id"] == service_id
        
        # Actualizar
        update_data = {"precio_clp": 40000, "descripcion": "Masaje actualizado"}
        response = await admin_client.patch(f"/admin/services/{service_id}", json=update_data)
        assert response.status_code == 200
        updated = response.json()
        assert updated["precio_clp"] == 40000
        assert updated["descripcion"] == "Masaje actualizado"
        
        # Listar
        response = await admin_client.get("/admin/services")
        assert response.status_code == 200
        services = response.json()
        assert any(s["id"] == service_id for s in services)
        
        # Eliminar (soft delete)
        response = await admin_client.delete(f"/admin/services/{service_id}")
        assert response.status_code == 204
        
        # Verificar que está inactivo
        response = await admin_client.get(f"/admin/services/{service_id}")
        assert response.status_code == 200
        deleted = response.json()
        assert deleted["activo"] is False

    @pytest.mark.asyncio
    async def test_admin_professionals_crud(self, admin_client: AsyncClient, db_session):
        """Test: CRUD completo de profesionales."""
        # Crear servicio primero
        from src.models.service import Service
        service = Service(
            nombre="Test Servicio",
            categoria="masaje",
            duracion_min=60,
            precio_clp=35000,
            activo=True,
        )
        db_session.add(service)
        await db_session.flush()
        service_id = str(service.id)
        
        # Crear profesional
        prof_data = {
            "nombre": "Test Profesional",
            "google_calendar_id": None,
            "horario_semanal": {
                "1": [{"start": "09:00", "end": "13:00"}],
                "2": [{"start": "09:00", "end": "13:00"}],
            },
            "activo": True,
            "service_ids": [service_id],
        }
        
        response = await admin_client.post("/admin/professionals", json=prof_data)
        assert response.status_code == 201
        created = response.json()
        assert created["nombre"] == "Test Profesional"
        prof_id = created["id"]
        
        # Verificar asociación con servicio
        assert service_id in created["service_ids"]
        
        # Actualizar
        response = await admin_client.patch(
            f"/admin/professionals/{prof_id}",
            json={"nombre": "Test Profesional Actualizado"}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["nombre"] == "Test Profesional Actualizado"
        
        # Eliminar
        response = await admin_client.delete(f"/admin/professionals/{prof_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_admin_bookings_list(self, admin_client: AsyncClient, db_session):
        """Test: Listar reservas con filtros."""
        response = await admin_client.get("/admin/bookings")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        
        # Test con filtros
        response = await admin_client.get("/admin/bookings?estado=confirmed&page=1&size=10")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_bookings_update(self, admin_client: AsyncClient, db_session):
        """Test: Actualizar reserva (reprogramar/cancelar)."""
        from src.models import Service, Professional, Client, Booking, BookingStatus
        import datetime
        
        # Crear datos necesarios
        client = Client(
            nombre="Test Client",
            telefono="+56912345678",
            email="test@test.cl",
            consentimiento=True,
            fecha_alta=datetime.datetime.now().astimezone(),
        )
        service = Service(
            nombre="Test Service",
            categoria="masaje",
            duracion_min=60,
            precio_clp=35000,
            activo=True,
        )
        prof = Professional(
            nombre="Test Prof",
            horario_semanal={"1": [{"start": "09:00", "end": "13:00"}]},
            activo=True,
        )
        db_session.add_all([client, service, prof])
        await db_session.flush()
        
        booking = Booking(
            codigo="EST-20241120-001",
            client_id=client.id,
            service_id=service.id,
            professional_id=prof.id,
            inicio=datetime.datetime.now().astimezone() + datetime.timedelta(days=1),
            fin=datetime.datetime.now().astimezone() + datetime.timedelta(days=1, hours=1),
            estado=BookingStatus.CONFIRMED,
            origen="test",
        )
        db_session.add(booking)
        await db_session.flush()
        booking_id = str(booking.id)
        
        # Reprogramar
        new_time = datetime.datetime.now().astimezone() + datetime.timedelta(days=2, hours=2)
        response = await admin_client.patch(
            f"/admin/bookings/{booking_id}",
            json={"start_time": new_time.isoformat()}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["inicio"] == new_time.isoformat()
        
        # Cancelar
        response = await admin_client.delete(
            f"/admin/bookings/{booking_id}",
            params={"reason": "Test cancel"}
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_admin_stats_endpoints(self, admin_client: AsyncClient):
        """Test: Endpoints de estadísticas."""
        # Stats generales
        response = await admin_client.get("/admin/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "total_bookings" in stats
        assert "total_revenue" in stats
        assert "occupancy_rate" in stats
        
        # Reservas por día
        response = await admin_client.get("/admin/stats/bookings-by-day?days=7")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Popularidad de servicios
        response = await admin_client.get("/admin/stats/services-popularity")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Ingresos
        response = await admin_client.get("/admin/stats/revenue?days=30")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_day" in data
        assert "by_service" in data
        assert "by_professional" in data

    @pytest.mark.asyncio
    async def test_admin_auth_required(self):
        """Test: Endpoints admin requieren autenticación."""
        # Cliente sin API key
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/admin/stats")
            assert response.status_code == 401
            
            # API key incorrecta
            client.headers["X-Internal-Api-Key"] = "wrong-key"
            response = await client.get("/admin/stats")
            assert response.status_code == 401


# Configuración pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "admin: tests del panel administrativo")