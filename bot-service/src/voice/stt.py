"""Speech-to-Text - Interfaces y implementaciones (Mock, Faster-Whisper, HuggingFace)."""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from ..config import settings
from ..utils import get_logger

logger = get_logger(__name__)


class SpeechToText(ABC):
    """Interfaz base para STT."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str = "es-CL") -> Optional[str]:
        """Transcribe audio a texto. Retorna None si falla."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible."""
        pass


class MockSTT(SpeechToText):
    """STT Mock para desarrollo - simula transcripción."""

    async def transcribe(self, audio_bytes: bytes, language: str = "es-CL") -> Optional[str]:
        # Simular delay de procesamiento
        import asyncio
        await asyncio.sleep(0.5)

        # En mock, retornamos texto basado en tamaño del audio
        # En realidad, esto sería reemplazado por transcripción real
        size_kb = len(audio_bytes) / 1024
        if size_kb < 10:
            return "Hola quiero agendar una hora"
        elif size_kb < 30:
            return "Quiero un masaje relajante para mañana en la mañana"
        else:
            return "Hola, me gustaría reservar un masaje descontracturante para el viernes a las tres de la tarde con María"

    def is_available(self) -> bool:
        return True


class FasterWhisperSTT(SpeechToText):
    """STT usando faster-whisper (local)."""

    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                logger.info("faster_whisper_model_loaded", model=self.model_size, device=self.device)
            except ImportError:
                logger.error("faster_whisper_not_installed")
                raise
            except Exception as e:
                logger.exception("faster_whisper_load_error", error=str(e))
                raise

    async def transcribe(self, audio_bytes: bytes, language: str = "es-CL") -> Optional[str]:
        import asyncio
        import tempfile
        import os

        # Ejecutar en thread pool para no bloquear
        loop = asyncio.get_event_loop()

        def _transcribe_sync():
            self._load_model()
            
            # Guardar audio a archivo temporal (faster-whisper necesita archivo)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                segments, info = self._model.transcribe(
                    tmp_path,
                    language="es" if language.startswith("es") else language,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                text = " ".join(segment.text for segment in segments).strip()
                logger.info("stt_transcribed", language=info.language, duration=info.duration, text_len=len(text))
                return text if text else None
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        try:
            return await loop.run_in_executor(None, _transcribe_sync)
        except Exception as e:
            logger.exception("faster_whisper_transcribe_error", error=str(e))
            return None

    def is_available(self) -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False


class HuggingFaceSTT(SpeechToText):
    """STT usando Hugging Face Inference API (gratuito con límites)."""

    def __init__(self, api_token: str, model_id: str = "openai/whisper-medium"):
        self.api_token = api_token
        self.model_id = model_id
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    async def transcribe(self, audio_bytes: bytes, language: str = "es-CL") -> Optional[str]:
        import httpx

        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    content=audio_bytes,
                )
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "").strip()
                    logger.info("hf_stt_transcribed", text_len=len(text))
                    return text if text else None
                elif response.status_code == 503:
                    # Modelo cargando, reintentar
                    import asyncio
                    await asyncio.sleep(10)
                    response = await client.post(self.api_url, headers=headers, content=audio_bytes)
                    if response.status_code == 200:
                        return response.json().get("text", "").strip()
                logger.warning("hf_stt_error", status=response.status_code, text=response.text[:200])
                return None
            except Exception as e:
                logger.exception("hf_stt_exception", error=str(e))
                return None

    def is_available(self) -> bool:
        return bool(self.api_token)


# Factory para obtener instancia según configuración
def get_stt_provider() -> SpeechToText:
    """Factory que retorna la instancia STT según configuración."""
    provider = settings.stt_provider.lower()

    if provider == "faster-whisper":
        return FasterWhisperSTT()
    elif provider == "huggingface":
        # Requiere HF_API_TOKEN en settings
        return HuggingFaceSTT(api_token=settings.huggingface_api_token or "")
    else:
        return MockSTT()


# Función de conveniencia para usar en handlers
async def transcribe_audio(audio_bytes: bytes, language: str = "es-CL") -> Optional[str]:
    """Transcribe audio usando el proveedor configurado."""
    provider = get_stt_provider()
    
    if not provider.is_available():
        logger.warning("stt_provider_unavailable", provider=settings.stt_provider)
        return None

    try:
        return await provider.transcribe(audio_bytes, language)
    except Exception as e:
        logger.exception("stt_transcribe_error", provider=settings.stt_provider, error=str(e))
        return None