"""Tests de integración para funcionalidad de voz (Fase 5)."""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Message, Chat, Voice
from telegram.ext import ContextTypes

from src.voice.stt import transcribe_audio, MockSTT, get_stt_provider
from src.voice.tts import synthesize_speech, MockTTS, get_tts_provider
from src.agent.core import run_agent_turn
from src.bot.handler import handle_voice_message, cmd_voz


@pytest_asyncio.fixture
async def mock_update():
    """Crea un Update mock de Telegram con mensaje de voz."""
    user = User(id=123456789, first_name="Test", is_bot=False, username="testuser")
    chat = Chat(id=123456789, type="private")
    voice = Voice(
        file_id="voice_123",
        file_unique_id="voice_unique_123",
        duration=10,
        file_size=1024,
    )
    message = Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=chat,
        from_user=user,
        voice=voice,
    )
    update = Update(update_id=1, message=message)
    return update


@pytest_asyncio.fixture
async def mock_context():
    """Crea un Context mock."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    context.bot = AsyncMock()
    return context


class TestSTT:
    """Tests para Speech-to-Text."""

    @pytest.mark.asyncio
    async def test_mock_stt_transcribe(self):
        """Test: Mock STT transcribe returns expected text based on audio size."""
        stt = MockSTT()
        
        # Audio pequeño (< 10KB)
        small_audio = b"x" * 5000  # 5KB
        result = await stt.transcribe(small_audio)
        assert result == "Hola quiero agendar una hora"
        
        # Audio mediano (< 30KB)
        medium_audio = b"x" * 20000  # 20KB
        result = await stt.transcribe(medium_audio)
        assert "masaje relajante" in result.lower()
        
        # Audio grande (>= 30KB)
        large_audio = b"x" * 40000  # 40KB
        result = await stt.transcribe(large_audio)
        assert "masaje descontracturante" in result.lower()

    @pytest.mark.asyncio
    async def test_get_stt_provider_mock(self):
        """Test: Factory returns MockSTT when provider is mock."""
        with patch("src.voice.stt.settings.stt_provider", "mock"):
            provider = get_stt_provider()
            assert isinstance(provider, MockSTT)
            assert provider.is_available() is True

    @pytest.mark.asyncio
    async def test_transcribe_audio_function(self):
        """Test: transcribe_audio function delegates to provider."""
        with patch("src.voice.stt.get_stt_provider") as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.transcribe.return_value = "Hola mundo"
            mock_get_provider.return_value = mock_provider
            
            result = await transcribe_audio(b"audio_data")
            assert result == "Hola mundo"
            mock_provider.transcribe.assert_called_once()


class TestTTS:
    """Tests para Text-to-Speech."""

    @pytest.mark.asyncio
    async def test_mock_tts_synthesize(self):
        """Test: Mock TTS returns audio bytes."""
        tts = MockTTS()
        
        audio = await tts.synthesize("Hola mundo")
        assert isinstance(audio, bytes)
        assert len(audio) > 0
        assert tts.is_available() is True

    @pytest.mark.asyncio
    async def test_get_tts_provider_mock(self):
        """Test: Factory returns MockTTS when provider is mock."""
        with patch("src.voice.tts.settings.tts_provider", "mock"):
            provider = get_tts_provider()
            assert isinstance(provider, MockTTS)
            assert provider.is_available() is True

    @pytest.mark.asyncio
    async def test_synthesize_speech_function(self):
        """Test: synthesize_speech function delegates to provider."""
        with patch("src.voice.tts.get_tts_provider") as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.synthesize.return_value = b"audio_bytes"
            mock_get_provider.return_value = mock_provider
            
            result = await synthesize_speech("Hola mundo")
            assert result == b"audio_bytes"
            mock_provider.synthesize.assert_called_once_with("Hola mundo", "es-CL")


class TestVoiceIntegration:
    """Tests de integración end-to-end para voz."""

    @pytest.mark.asyncio
    async def test_handle_voice_message_flow(self, mock_update, mock_context):
        """Test: Flujo completo de manejo de mensaje de voz."""
        # Mock STT
        with patch("src.bot.handler.transcribe_audio") as mock_transcribe:
            mock_transcribe.return_value = "Quiero un masaje relajante para mañana a las 10"
            
            # Mock agent response
            mock_response = MagicMock()
            mock_response.messages = [
                MagicMock(type="text", content="¡Entendido! ¿Quieres agendar un masaje relajante para mañana a las 10:00?")
            ]
            
            with patch("src.bot.handler.run_agent_turn", return_value=mock_response):
                await handle_voice_message(mock_update, mock_context)
                
                # Verificar que se llamó a STT
                mock_transcribe.assert_called_once()
                
                # Verificar que se envió mensaje de confirmación
                mock_update.message.reply_html.assert_called()
                call_args = mock_update.message.reply_html.call_args[0][0]
                assert "Entendido" in call_args
                assert "masaje relajante" in call_args

    @pytest.mark.asyncio
    async def test_voice_too_long_rejected(self, mock_update, mock_context):
        """Test: Notas de voz > 60s son rechazadas."""
        mock_update.message.voice.duration = 65
        
        await handle_voice_message(mock_update, mock_context)
        
        mock_update.message.reply_html.assert_called()
        call_args = mock_update.message.reply_html.call_args[0][0]
        assert "muy larga" in call_args
        assert "60 segundos" in call_args

    @pytest.mark.asyncio
    async def test_voice_stt_failure_handled(self, mock_update, mock_context):
        """Test: Fallo en STT se maneja graciosamente."""
        with patch("src.bot.handler.transcribe_audio") as mock_transcribe:
            mock_transcribe.side_effect = Exception("STT failed")
            
            await handle_voice_message(mock_update, mock_context)
            
            mock_update.message.reply_html.assert_called()
            call_args = mock_update.message.reply_html.call_args[0][0]
            assert "No pude entender" in call_args

    @pytest.mark.asyncio
    async def test_voice_empty_transcript_handled(self, mock_update, mock_context):
        """Test: Transcripción vacía se maneja graciosamente."""
        with patch("src.bot.handler.transcribe_audio") as mock_transcribe:
            mock_transcribe.return_value = "  "  # Solo espacios
            
            await handle_voice_message(mock_update, mock_context)
            
            mock_update.message.reply_html.assert_called()
            call_args = mock_update.message.reply_html.call_args[0][0]
            assert "No se detectó voz clara" in call_args


class TestVoiceCommands:
    """Tests para comandos de voz."""

    @pytest.mark.asyncio
    async def test_cmd_voz_on(self):
        """Test: /voz on activa respuestas de voz."""
        update = MagicMock()
        update.effective_user = User(id=123, first_name="Test", is_bot=False)
        update.message = MagicMock()
        update.message.reply_html = AsyncMock()
        
        context = MagicMock()
        context.args = ["on"]
        context.user_data = {}
        
        await cmd_voz(update, context)
        
        assert context.user_data["voice_enabled"] is True
        update.message.reply_html.assert_called()
        call_args = update.message.reply_html.call_args[0][0]
        assert "activado" in call_args

    @pytest.mark.asyncio
    async def test_cmd_voz_off(self):
        """Test: /voz off desactiva respuestas de voz."""
        update = MagicMock()
        update.effective_user = User(id=123, first_name="Test", is_bot=False)
        update.message = MagicMock()
        update.message.reply_html = AsyncMock()
        
        context = MagicMock()
        context.args = ["off"]
        context.user_data = {}
        
        await cmd_voz(update, context)
        
        assert context.user_data["voice_enabled"] is False
        update.message.reply_html.assert_called()
        call_args = update.message.reply_html.call_args[0][0]
        assert "desactivado" in call_args

    @pytest.mark.asyncio
    async def test_cmd_voz_invalid_arg(self):
        """Test: /voz sin argumento muestra ayuda."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_html = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {}
        
        await cmd_voz(update, context)
        
        update.message.reply_html.assert_called()
        call_args = update.message.reply_html.call_args[0][0]
        assert "Uso:" in call_args


class TestAgentVoiceResponse:
    """Tests para respuestas de voz del agente."""

    @pytest.mark.asyncio
    async def test_agent_returns_voice_message(self):
        """Test: Agente puede retornar mensaje de voz."""
        from src.agent.schemas import AgentMessage, AgentResponse
        
        response = AgentResponse(
            messages=[
                AgentMessage(type="text", content="Texto de respuesta"),
                AgentMessage(type="voice", content="Audio de respuesta", audio_bytes=b"audio_data", caption="Tu reserva"),
            ],
            tool_calls=[],
            should_handoff=False,
        )
        
        assert len(response.messages) == 2
        assert response.messages[0].type == "text"
        assert response.messages[1].type == "voice"
        assert response.messages[1].audio_bytes == b"audio_data"


# Fixtures compartidas
@pytest_asyncio.fixture
async def mock_update_fixture():
    """Fixture reutilizable para Update mock con voz."""
    user = User(id=123456789, first_name="Test", is_bot=False, username="testuser")
    chat = Chat(id=123456789, type="private")
    voice = Voice(
        file_id="voice_123",
        file_unique_id="voice_unique_123",
        duration=10,
        file_size=1024,
    )
    message = Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=chat,
        from_user=User(id=123456789, first_name="Test", is_bot=False),
        voice=voice,
    )
    return Update(update_id=1, message=message)


@pytest_asyncio.fixture
async def mock_context_fixture():
    """Fixture reutilizable para Context mock."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    context.bot = AsyncMock()
    return context


# Imports necesarios
import datetime
from unittest.mock import AsyncMock, MagicMock, patch, MagicMock
from telegram import User, Chat, Message, Voice, Update
from telegram.ext import ContextTypes
import datetime

# Configuración pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "voice: tests de funcionalidad de voz")
    config.addinivalue_line("markers", "integration: tests de integración")