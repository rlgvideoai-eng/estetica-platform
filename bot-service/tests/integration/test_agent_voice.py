"""Tests para la integración de voz en el Agent Core."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.core import run_agent_turn, agent_core, AgentCore
from src.agent.schemas import AgentResponse, AgentMessage


class TestAgentVoiceResponse:
    """Tests para respuestas de voz del agente."""

    @pytest.mark.asyncio
    async def test_agent_returns_voice_when_enabled(self):
        """Test: Agente retorna mensaje de voz cuando el usuario tiene voice_enabled."""
        # Mock LLM response con tool calls
        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.tool_calls = []
        mock_llm_response.choices[0].message.content = None
        
        # Segunda llamada (final) retorna JSON con mensaje de voz
        mock_final_response = MagicMock()
        mock_final_response.choices = [MagicMock()]
        mock_final_response.choices[0].message.content = '{"messages": [{"type": "voice", "content": "Tu reserva ha sido confirmada para mañana a las 10:00", "audio_bytes": "base64_audio_data", "caption": "Confirmación de reserva"}], "tool_calls": [], "should_handoff": false, "handoff_summary": null}'
        
        with patch("src.agent.core.llm_client.chat.completions.create") as mock_create:
            mock_create.side_effect = [mock_llm_response, mock_final_response]
            
            # Mock tool execution (no tool calls in this case)
            with patch.object(agent_core, '_execute_tool') as mock_tool:
                mock_tool.return_value = MagicMock()
                
                response = await run_agent_turn(
                    user_id=123456789,
                    chat_id=123456789,
                    user_text="Confirma mi reserva",
                    context_data={"voice_enabled": True},
                )
                
                # Verificar que la respuesta incluye mensaje de voz
                assert len(response.messages) >= 1
                voice_messages = [m for m in response.messages if m.type == "voice"]
                assert len(voice_messages) >= 1
                voice_msg = voice_messages[0]
                assert voice_msg.type == "voice"
                assert voice_msg.content is not None
                assert voice_msg.caption is not None

    @pytest.mark.asyncio
    async def test_agent_no_voice_when_disabled(self):
        """Test: Agente NO retorna voz cuando voice_enabled=False."""
        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.tool_calls = []
        mock_llm_response.choices[0].message.content = None
        
        mock_final_response = MagicMock()
        mock_final_response.choices = [MagicMock()]
        mock_final_response.choices[0].message.content = '{"messages": [{"type": "text", "content": "Tu reserva ha sido confirmada"}], "tool_calls": [], "should_handoff": false, "handoff_summary": null}'
        
        with patch("src.agent.core.llm_client.chat.completions.create") as mock_create:
            mock_create.side_effect = [mock_llm_response, mock_final_response]
            
            with patch.object(agent_core, '_execute_tool') as mock_tool:
                mock_tool.return_value = MagicMock()
                
                response = await run_agent_turn(
                    user_id=123456789,
                    chat_id=123456789,
                    user_text="Confirma mi reserva",
                    context_data={"voice_enabled": False},  # VOICE DISABLED
                )
                
                # Verificar que NO hay mensajes de voz
                voice_messages = [m for m in response.messages if m.type == "voice"]
                assert len(voice_messages) == 0
                text_messages = [m for m in response.messages if m.type == "text"]
                assert len(text_messages) >= 1


class TestAgentCoreVoiceIntegration:
    """Tests de integración del AgentCore con voz."""

    @pytest.mark.asyncio
    async def test_agent_creates_voice_response_for_confirmation(self):
        """Test: Agente genera respuesta de voz al confirmar reserva."""
        # Mock LLM responses
        mock_first = MagicMock()
        mock_first.choices = [MagicMock()]
        mock_first.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="create_booking",
                    arguments='{"service_id": "svc-1", "start_time": "2024-11-25T10:00:00", "professional_id": "prof-1", "client": {"nombre": "María", "telefono": "+56912345678", "email": "maria@test.cl", "telegram_user_id": 123456789}, "idempotency_key": "test-key"}',
                ),
                id="call_1",
            )
        ]
        
        mock_final = MagicMock()
        mock_final.choices = [MagicMock()]
        mock_final.choices[0].message.content = '{"messages": [{"type": "text", "content": "¡Reserva confirmada! Código: EST-20241120-001"}, {"type": "voice", "content": "Tu reserva ha sido confirmada para mañana a las 10:00. Código EST-20241120-001.", "caption": "Confirmación de reserva"}], "tool_calls": [{"tool": "create_booking", "input": {"service_id": "svc-1", "start_time": "2024-11-25T10:00:00"}, "output": {"success": true}}], "should_handoff": false, "handoff_summary": null}'
        
        with patch("src.agent.core.llm_client.chat.completions.create") as mock_create:
            mock_create.side_effect = [mock_first, mock_final]
            
            with patch.object(agent_core, '_execute_tool') as mock_tool:
                mock_tool.return_value = MagicMock(
                    success=True,
                    booking=MagicMock(
                        codigo="EST-20241120-001",
                        service_name="Masaje Relajante",
                        professional_name="María",
                        precio=35000,
                        inicio="2024-11-25T10:00:00",
                    )
                )
                
                response = await run_agent_turn(
                    user_id=123456789,
                    chat_id=123456789,
                    user_text="Sí, confirmo mi reserva",
                    context_data={"voice_enabled": True, "selected_slot": {"service_id": "svc-1", "start_time": "2024-11-25T10:00:00", "professional_id": "prof-1"}},
                )
                
                # Verificar respuesta incluye voz
                voice_msgs = [m for m in response.messages if m.type == "voice"]
                assert len(voice_msgs) >= 1
                voice_msg = voice_msgs[0]
                assert "confirmada" in voice_msg.content.lower()
                assert voice_msg.caption is not None


# Fixtures
@pytest_asyncio.fixture
async def mock_context():
    context = MagicMock()
    context.args = []
    context.user_data = {}
    context.bot = AsyncMock()
    return context


# Configuración pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "voice: tests de funcionalidad de voz")
    config.addinivalue_line("markers", "agent: tests del agente core")