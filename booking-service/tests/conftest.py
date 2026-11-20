"""Configuración pytest para booking-service."""
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Configurar variables de entorno para tests ANTES de importar settings
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://estetica:estetica@localhost:5432/estetica_test")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")
os.environ.setdefault("GOOGLE_REFRESH_TOKEN", "test")
os.environ.setdefault("EMAIL_FROM", "test@test.cl")
os.environ.setdefault("EMAIL_PROVIDER_KEY", "")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.cl")
os.environ.setdefault("TIMEZONE", "America/Santiago")
os.environ.setdefault("CANCEL_MIN_HOURS", "24")
os.environ.setdefault("BOOKING_MAX_HORIZON_DAYS", "60")
os.environ.setdefault("GRID_SIZE_MINUTES", "15")
os.environ.setdefault("MAX_ACTIVE_BOOKINGS_PER_CLIENT", "3")

from src.config import settings
from src.db.base import Base
from src.db.session import get_engine, get_session_factory, init_db, close_db
from src.models import (
    Service, Professional, ProfessionalService,
    BusinessHours, TimeBlock, Client, Booking, ConversationLog
)


# Engine global para tests
_test_engine = None
_test_session_factory = None


def get_test_engine():
    global _test_engine
    if _test_engine is None:
        _test_engine = create_async_engine(
            settings.database_url,
            echo=False,
            poolclass=NullPool,
        )
    return _test_engine


def get_test_session_factory():
    global _test_session_factory
    if _test_session_factory is None:
        _test_session_factory = async_sessionmaker(
            get_test_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _test_session_factory


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Crea tablas en BD de test una vez por sesión."""
    engine = get_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup al final
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Provee sesión de BD con transacción que se hace rollback al final."""
    factory = get_test_session_factory()
    async with factory() as session:
        # Iniciar transacción
        async with session.begin():
            yield session
            # Rollback automático al salir del context manager


@pytest_asyncio.fixture
async def test_business_hours(db_session):
    """Crea horarios de negocio para tests."""
    from src.models import BusinessHours
    hours = []
    for day in range(7):  # 0=Dom ... 6=Sáb
        if day == 0 or day == 6:  # Dom/Sáb - horario reducido
            tramos = [{"start": "09:00", "end": "14:00"}]
        else:  # Lun-Vie
            tramos = [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "19:00"}]
        
        bh = BusinessHours(
            dia_semana=day,
            tramos=tramos,
            excepciones=[],
            activo=True,
        )
        db_session.add(bh)
        hours.append(bh)
    
    await db_session.flush()
    return hours


# Configuración de pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: tests de integración")
    config.addinivalue_line("markers", "unit: tests unitarios")
    config.addinivalue_line("markers", "slow: tests lentos")