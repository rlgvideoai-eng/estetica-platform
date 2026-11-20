"""Configuración pytest para bot-service."""
import os
import sys
from pathlib import Path

# Configurar variables de entorno ANTES de importar módulos
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("ADMIN_TELEGRAM_CHAT_ID", "123456789")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "nemotron-nano-omni")
os.environ.setdefault("DATABRICKS_RAG_URL", "http://rag-mock:8000")
os.environ.setdefault("DATABRICKS_TOKEN", "test")
os.environ.setdefault("BOOKING_SERVICE_URL", "http://booking-service:8000")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.cl")
os.environ.setdefault("TIMEZONE", "America/Santiago")
os.environ.setdefault("STT_PROVIDER", "mock")
os.environ.setdefault("TTS_PROVIDER", "mock")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from telegram import User, Chat, Message, CallbackQuery, Update


@pytest_asyncio.fixture
async def mock_user():
    """Usuario de Telegram mock."""
    return User(
        id=123456789,
        first_name="Test",
        last_name="User",
        username="testuser",
        is_bot=False,
        language_code="es-CL",
    )


@pytest_asyncio.fixture
async def mock_chat():
    """Chat de Telegram mock."""
    return Chat(
        id=123456789,
        type="private",
        first_name="Test",
        username="testuser",
    )


@pytest_asyncio.fixture
async def mock_message(mock_user, mock_chat):
    """Mensaje de Telegram mock."""
    return Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=mock_chat,
        from_user=mock_user,
        text="/start",
    )


@pytest_asyncio.fixture
async def mock_update(mock_message):
    """Update de Telegram mock."""
    return Update(update_id=1, message=mock_message)


@pytest_asyncio.fixture
async def mock_context():
    """Context de Telegram mock."""
    context = MagicMock()
    context.args = []
    context.user_data = {}
    context.bot = AsyncMock()
    return context


@pytest_asyncio.fixture
async def mock_callback_query(mock_user, mock_message):
    """CallbackQuery mock."""
    query = MagicMock()
    query.id = "callback_1"
    query.from_user = mock_user
    query.message = mock_message
    query.data = "test:data"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


# Configuración pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: tests de integración")
    config.addinivalue_line("markers", "unit: tests unitarios")
    config.addinivalue_line("markers", "slow: tests lentos")