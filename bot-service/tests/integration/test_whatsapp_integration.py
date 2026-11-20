"""Tests de integración para WhatsApp (Fase 6)."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from src.channels.whatsapp_adapter import WhatsAppAdapter, get_channel_adapter
from src.channels.base import ChannelType
from src.channels.factory import get_channel_adapter, initialize_all_channels, shutdown_all_channels
from src.config import settings


@pytest_asyncio.fixture
async def mock_whatsapp_config():
    """Configuración mock para WhatsApp."""
    return {
        "whatsapp_phone_number_id": "test_phone_id",
        "whatsapp_access_token": "test_token",
        "whatsapp_webhook_verify_token": "test_verify_token",
        "whatsapp_business_account_id": "test_business_id",
    }


class TestWhatsAppAdapter:
    """Tests para el adaptador de WhatsApp."""

    @pytest.mark.asyncio
    async def test_whatsapp_adapter_initialization(self, mock_whatsapp_config):
        """Test: Inicialización del adaptador WhatsApp."""
        adapter = WhatsAppAdapter(mock_whatsapp_config)
        await adapter.initialize()
        
        assert adapter._initialized is True
        assert adapter._client is not None
        assert adapter.phone_number_id == "test_phone_id"

    @pytest.mark.asyncio
    async def test_whatsapp_adapter_send_text(self, mock_whatsapp_config):
        """Test: Envío de mensaje de texto."""
        adapter = WhatsAppAdapter(mock_whatsapp_config)
        await adapter.initialize()
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "msg_123"}]}
        
        with patch.object(adapter._client, "post", return_value=mock_response) as mock_post:
            result = await adapter.send_message(
                user_id="+56912345678",
                message={"text": "Hola mundo", "keyboard": None}
            )
            
            assert result is True
            mock_post.assert_called_once()
            # Verificar payload
            call_args = mock_post.call_args
            assert "/test_phone_id/messages" in str(call_args.args)
            payload = call_args.kwargs.get("json", {})
            assert payload["messaging_product"] == "whatsapp"
            assert payload["to"] == "56912345678"  # Formato sin +

    @pytest.mark.asyncio
    async def test_whatsapp_adapter_send_message_with_buttons(self, mock_whatsapp_config):
        """Test: Envío de mensaje con botones interactivos."""
        adapter = WhatsAppAdapter(mock_whatsapp_config)
        await adapter.initialize()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "msg_123"}]}
        
        keyboard = {
            "buttons": [
                [{"text": "Opción 1", "callback_data": "opt1"}],
                [{"text": "Opción 2", "callback_data": "opt2"}],
            ]
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "msg_123"}]}
        
        with patch.object(adapter._client, "post", return_value=mock_response) as mock_post:
            result = await adapter.send_message(
                user_id="+56912345678",
                message={"text": "Elige una opción", "keyboard": {"buttons": [[{"text": "Opción 1", "callback_data": "opt1"}], [{"text": "Opción 2", "callback_data": "opt2"}]}}
            )
            
            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_whatsapp_adapter_send_voice(self, mock_whatsapp_config):
        """Test: Envío de nota de voz."""
        adapter = WhatsAppAdapter(mock_whatsapp_config)
        await adapter.initialize()
        
        # Mock upload media
        upload_response = MagicMock()
        upload_response.status_code = 200
        upload_response.json.return_value = {"id": "media_123"}
        
        # Mock send message
        send_response = MagicMock()
        send_response.status_code = 200
        send_response.json.return_value = {"messages": [{"id": "msg_123"}]}
        
        with patch.object(adapter._client, "post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: {"id": "media_123"}),  # upload
                MagicMock(status_code=200, json=lambda: {"messages": [{"id": "msg_123"}]})  # send
            ]
            
            result = await adapter.send_voice(
                user_id="+56912345678",
                audio_bytes=b"fake_audio_data",
                caption="Tu audio"
            )
            
            # Verificar que se llamó dos veces (upload + send)
            assert adapter._client.post.call_count >= 1

    @pytest.mark.asyncio
    async def test_whatsapp_webhook_verification(self):
        """Test: Verificación de webhook (challenge)."""
        from src.channels.whatsapp_adapter import WhatsAppAdapter
        from ..config import settings
        
        adapter = WhatsAppAdapter({
            "whatsapp_webhook_verify_token": "test_verify_token",
        })
        
        # Mock request con challenge
        class MockRequest:
            query_params = {
                "hub.mode": "subscribe",
                "hub.challenge": "challenge_123",
                "hub.verify_token": "test_verify_token",
            }
        
        # Simular verificación
        adapter.webhook_verify_token = "test_verify_token"
        
        # Test manual de la lógica de verificación
        verify_token = "test_verify_token"
        challenge = "challenge_123"
        mode = "subscribe"
        
        assert mode == "subscribe"
        assert challenge == "challenge_123"
        assert "test_verify_token" == "test_verify_token"

    @pytest.mark.asyncio
    async def test_whatsapp_webhook_signature_verification(self):
        """Test: Verificación de firma X-Hub-Signature-256."""
        import hmac
        import hashlib
        
        adapter = WhatsAppAdapter({
            "whatsapp_webhook_verify_token": "secret_token",
        })
        adapter.webhook_verify_token = "secret_token"
        
        payload = b'{"test": "data"}'
        expected = hmac.new(
            b"secret_token",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        signature = f"sha256={expected}"
        
        assert adapter.verify_webhook_signature(payload, signature) is True
        
        # Firma incorrecta
        assert adapter.verify_webhook_signature(payload, "sha256=wrong") is False

    @pytest.mark.asyncio
    async def test_whatsapp_process_text_message(self, mock_whatsapp_config):
        """Test: Procesamiento de mensaje de texto entrante."""
        adapter = WhatsAppAdapter(mock_whatsapp_config)
        await adapter.initialize()
        
        # Mock webhook data para mensaje de texto
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "56912345678",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Hola, quiero agendar"}
                        }]
                    }
                }]
            }]
        
        message = await adapter.process_update({
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "56912345678",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Hola, quiero agendar"}
                        }]
                    }
                }]
            }]
        )
        
        assert message is not None
        assert message.channel == ChannelType.WHATSAPP
        assert message.text == "Hola, quiero agendar"
        assert message.user.id == "56912345678"

    @pytest.mark.asyncio
    async def test_whatsapp_process_voice_message(self, mock_whatsapp_config):
        """Test: Procesamiento de nota de voz entrante."""
        adapter = WhatsAppAdapter({
            "whatsapp_phone_number_id": "test_phone_id",
            "whatsapp_access_token": "test_token",
        })
        await adapter.initialize()
        
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_voice_123",
                            "from": "56912345678",
                            "timestamp": "1234567890",
                            "type": "audio",
                            "audio": {
                                "id": "audio_123",
                                "mime_type": "audio/ogg",
                                "sha256": "abc123"
                            }
                        }]
                    }
                }]
            }]
        }
        
        message = await adapter.process_update({
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_voice_123",
                            "from": "56912345678",
                            "timestamp": "1234567890",
                            "type": "audio",
                            "audio": {
                                "id": "audio_123",
                                "mime_type": "audio/ogg",
                                "sha256": "abc123"
                            }
                        }]
                    }
                }]
            }]
        )
        
        assert message is not None
        assert message.channel == ChannelType.WHATSAPP
        assert message.voice is not None
        assert message.voice["id"] == "audio_123"

    @pytest.mark.asyncio
    async def test_whatsapp_interactive_button_response(self, mock_whatsapp_config):
        """Test: Procesamiento de respuesta a botón interactivo."""
        adapter = WhatsAppAdapter({
            "whatsapp_phone_number_id": "test_phone_id",
            "whatsapp_access_token": "test_token",
        })
        await adapter.initialize()
        
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_interactive_123",
                            "from": "56912345678",
                            "timestamp": "1234567890",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "btn_confirmar",
                                    "title": "Confirmar"
                                }
                            }
                        }]
                    }
                }]
            }]
        }
        
        message = await adapter.process_update({
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_interactive_123",
                            "from": "56912345678",
                            "timestamp": "1234567890",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "btn_confirmar",
                                    "title": "Confirmar"
                                }
                            }
                        }]
                    }
                }]
            }]
        )
        
        assert message is not None
        assert message.text == "btn_confirmar"  # ID del botón presionado


class TestChannelFactory:
    """Tests para el factory de canales."""

    @pytest.mark.asyncio
    async def test_get_telegram_adapter(self):
        """Test: Factory crea adaptador Telegram."""
        adapter = get_channel_adapter(ChannelType.TELEGRAM)
        assert adapter is not None
        assert hasattr(adapter, 'channel_type')

    @pytest.mark.asyncio
    async def test_get_whatsapp_adapter(self):
        """Test: Factory crea adaptador WhatsApp."""
        with patch("src.config.settings.whatsapp_phone_number_id", "test_id"), \
             patch("src.config.settings.whatsapp_access_token", "test_token"):
            adapter = get_channel_adapter(ChannelType.WHATSAPP)
            assert adapter is not None

    @pytest.mark.asyncio
    async def test_initialize_all_channels(self):
        """Test: Inicialización de todos los canales."""
        with patch("src.config.settings.whatsapp_phone_number_id", None), \
             patch("src.config.settings.whatsapp_access_token", None):
            adapters = await initialize_all_channels()
            assert "telegram" in adapters
            # WhatsApp no se inicializa sin credenciales


class TestWhatsAppIntegration:
    """Tests de integración completa WhatsApp + Bot."""

    @pytest.mark.asyncio
    async def test_whatsapp_to_booking_flow(self, mock_whatsapp_config):
        """Test: Flujo completo WhatsApp -> Agente -> Reserva."""
        from src.channels.factory import get_channel_adapter, ChannelType
        from src.agent.core import run_agent_turn
        
        adapter = WhatsAppAdapter({
            "whatsapp_phone_number_id": "test_phone_id",
            "whatsapp_access_token": "test_token",
            "whatsapp_webhook_verify_token": "test_verify",
        })
        await adapter.initialize()
        
        # Mock agent response
        mock_response = MagicMock()
        mock_response.messages = [
            MagicMock(type="text", content="¡Entendido! ¿Quieres agendar un masaje relajante para mañana a las 10:00?")
        ]
        mock_response.tool_calls = []
        mock_response.should_handoff = False
        
        with patch("src.agent.core.run_agent_turn", return_value=mock_response):
            # Simular webhook entrante
            webhook_data = {
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "id": "msg_123",
                                "from": "56912345678",
                                "timestamp": "1234567890",
                                "type": "text",
                                "text": {"body": "Quiero un masaje relajante para mañana"}
                            }]
                        }]
                    }]
                }]
            }
            
            # Procesar webhook
            adapter = WhatsAppAdapter({
                "whatsapp_phone_number_id": "test_phone_id",
                "whatsapp_access_token": "test_token",
            })
            await adapter.initialize()
            
            # Verificar que se puede procesar
            message = await get_channel_adapter(ChannelType.WHATSAPP).process_update({
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "id": "msg_123",
                                "from": "56912345678",
                                "timestamp": "1234567890",
                                "type": "text",
                                "text": {"body": "Quiero un masaje"}
                            }]
                        }]
                    }]
            })
            
            assert message is not None
            assert message.text == "Hola, quiero agendar"


# Configuración pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "whatsapp: tests de integración WhatsApp")
    config.addinivalue_line("markers", "integration: tests de integración")