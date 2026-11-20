"""Tests de integración Bot Service ↔ Booking Service."""
import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes

from src.agent.core import run_agent_turn, agent_core
from src.agent.schemas import AgentResponse, AgentMessage
from src.booking.client import create_booking, check_availability, list_services

from src.bot.handler import (
    cmd_start,
    handle_callback_query,
    handle_text_message,
    handle_voice_message,
)
from src.agent.core import run_agent_turn, agent_core
from src.agent.schemas import AgentResponse, AgentMessage
from src.booking.client import create_booking, check_availability, list_services


@pytest_asyncio.fixture
async def mock_update():
    """Crea un Update mock de Telegram."""
    user = User(id=123456789, first_name="Test", is_bot=False, username="testuser")
    chat = Chat(id=123456789, type="private")
    message = Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=chat,
        from_user=user,
        text="/start",
    )
    update = Update(update_id=1, message=message)
    return update


@pytest_asyncio.fixture
async def mock_context():
    """Crea un Context mock."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    return context


class TestBotBookingIntegration:
    """Tests de integración entre Bot y Booking Service."""

    @pytest.mark.asyncio
    async def test_start_command_initializes_user_data(
        self,
        mock_update: Update,
        mock_context: ContextTypes.DEFAULT_TYPE,
    ):
        """Test: /start inicializa user_data correctamente."""
        await cmd_start(mock_update, mock_context)
        
        assert "origen" in mock_context.user_data
        assert mock_context.user_data["origen"] == "directo"
        assert mock_context.user_data["telegram_user_id"] == 123456789
        
        # Verificar que se envió mensaje de bienvenida
        mock_update.message.reply_html.assert_called()
        call_args = mock_update.message.reply_html.call_args
        assert "Ayudio" in call_args[0][0]
        assert "Bienvenid@" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_start_with_landing_origin(
        self,
        mock_update: Update,
        mock_context: ContextTypes.DEFAULT_TYPE,
    ):
        """Test: /start con parámetro de origen (desde landing)."""
        mock_context.args = ["landing"]
        
        await cmd_start(mock_update, mock_context)
        
        assert mock_context.user_data["origen"] == "landing"

    @pytest.mark.asyncio
    async def test_callback_query_service_selection(
        self,
        mock_update: Update,
        mock_context: ContextTypes.DEFAULT_TYPE,
    ):
        """Test: Selección de servicio via callback query."""
        # Mock query
        query = AsyncMock(spec=CallbackQuery)
        query.data = "service:masajes"
        query.from_user = mock_update.effective_user
        query.message = mock_update.message
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        
        mock_update.callback_query = query
        
        # Mock servicio disponible
        with patch("src.bot.handler._show_availability") as mock_show:
            await handle_callback_query(mock_update, mock_context)
            
            mock_show.assert_called_once()
            assert mock_context.user_data["selected_service_id"] == "masajes"

    @pytest.mark.asyncio
    async def test_agent_booking_flow_mock(
        self,
        mock_update: Update,
        mock_context: ContextTypes.DEFAULT_TYPE,
    ):
        """Test: Flujo completo de reserva via agente (mock)."""
        # Mock respuesta del agente
        mock_response = MagicMock()
        mock_response.messages = [
            MagicMock(type="text", content="¡Reserva confirmada! Código: EST-20241120-001")
        ]
        mock_response.tool_calls = [
            {"tool": "check_availability", "output": {"slots": []}},
            {"tool": "create_booking", "output": {"success": True, "booking": {"codigo": "EST-20241120-001"}}},
        ]
        mock_response.should_handoff = False
        
        with patch("src.agent.core.run_agent_turn", return_value=mock_response):
            mock_update.message.text = "Quiero un masaje relajante para mañana a las 10"
            await handle_text_message(mock_update, mock_context)
            
            mock_update.message.reply_html.assert_called()
            call_args = mock_update.message.reply_html.call_args[0][0]
            assert "confirmada" in call_args.lower() or "reserva" in call_args.lower()


class TestAgentCore:
    """Tests unitarios del AgentCore."""

    @pytest.mark.asyncio
    async def test_run_agent_turn_booking_flow(self):
        """Test: Turno del agente para flujo de reserva."""
        # Mock LLM response con tool calls
        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="list_services",
                    arguments="{}",
                ),
                id="call_1",
            ),
            MagicMock(
                function=MagicMock(
                    name="check_availability",
                    arguments='{"service_id": "test-id", "from_date": "2024-11-21T10:00:00", "to_date": "2024-11-21T14:00:00"}',
                ),
                id="call_2",
            ),
        ]
        
        with patch("src.agent.core.llm_client.chat.completions.create", return_value=mock_llm_response):
            with patch("src.agent.core.agent_core._execute_tool") as mock_tool:
                mock_tool.side_effect = [
                    MagicMock(services=[MagicMock(id="test-id", nombre="Masaje", duracion_min=60, precio_clp=35000)]),
                    MagicMock(slots=[MagicMock(start_iso="2024-11-21T10:00:00", end_iso="2024-11-21T11:00:00", date_str="21/11/2024", time_str="10:00", professional_id="prof-1", professional_name="María")]),
                ]
                
                response = await run_agent_turn(
                    user_id=123456789,
                    chat_id=123456789,
                    user_text="Quiero un masaje para mañana en la mañana",
                    context_data={},
                )
                
                assert len(response.messages) > 0
                assert len(response.tool_calls) == 2


class TestBookingClient:
    """Tests del cliente HTTP a Booking Service."""

    @pytest.mark.asyncio
    async def test_list_services_mock(self):
        """Test: list_services usa mock en desarrollo."""
        from src.booking.client import list_services
        services = await list_services()
        assert isinstance(services, list)
        assert len(services) > 0
        assert all(hasattr(s, "id") for s in services)

    @pytest.mark.asyncio
    async def test_check_availability_mock(self):
        """Test: check_availability usa mock."""
        from src.booking.client import check_availability
        from datetime import datetime, timedelta
        
        slots = await check_availability(
            service_id="test-id",
            from_date=datetime.now() + timedelta(days=1),
            to_date=datetime.now() + timedelta(days=2),
        )
        assert isinstance(slots, list)
        assert len(slots) > 0

    @pytest.mark.asyncio
    async def test_create_booking_idempotent_mock(self):
        """Test: create_booking es idempotente en mock."""
        from src.booking.client import create_booking
        from datetime import datetime, timedelta
        
        client_data = {
            "nombre": "Test User",
            "telefono": "+56912345678",
            "email": "test@test.cl",
            "telegram_user_id": 123456789,
        }
        
        idempotency_key = f"test-{uuid.uuid4()}"
        
        # Primera creación
        result1 = await create_booking(
            service_id="test-id",
            start_time=(datetime.now() + timedelta(days=1)).isoformat(),
            professional_id="prof-1",
            client=client_data,
            idempotency_key=idempotency_key,
        )
        assert result1.success is True
        
        # Segunda con misma clave
        result2 = await create_booking(
            service_id="test-id",
            start_time=(datetime.now() + timedelta(days=1)).isoformat(),
            professional_id="prof-1",
            client=client_data,
            idempotency_key=idempotency_key,
        )
        assert result2.success is True
        assert result1.booking.id == result2.booking.id


# Fixtures compartidas
@pytest_asyncio.fixture
async def mock_update_fixture():
    """Fixture reutilizable para Update mock."""
    user = User(id=123456789, first_name="Test", is_bot=False, username="testuser")
    chat = Chat(id=123456789, type="private")
    message = Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=chat,
        from_user=user,
        text="",
    )
    return Update(update_id=1, message=message)


@pytest_asyncio.fixture
async def mock_context_fixture():
    """Fixture reutilizable para Context mock."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    return context


# Configuración pytest para este módulo
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: tests de integración bot-booking")