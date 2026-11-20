"""Text-to-Speech - Interfaces y implementaciones (Mock, Piper, HuggingFace, Browser)."""
import logging
import asyncio
import tempfile
import os
from abc import ABC, abstractmethod
from typing import Optional

from ..config import settings
from ..utils import get_logger

logger = get_logger(__name__)


class TextToSpeech(ABC):
    """Interfaz base para TTS."""

    @abstractmethod
    async def synthesize(self, text: str, language: str = "es-CL") -> Optional[bytes]:
        """Sintetiza texto a audio (OGG/Opus para Telegram). Retorna bytes o None si falla."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible."""
        pass


class MockTTS(TextToSpeech):
    """TTS Mock para desarrollo - genera audio silencioso corto."""

    async def synthesize(self, text: str, language: str = "es-CL") -> Optional[bytes]:
        # Simular delay
        await asyncio.sleep(0.3)
        
        # Generar OGG/Opus mínimo (silencio de 1 segundo)
        # En desarrollo real, esto sería audio real
        logger.debug("mock_tts_synthesized", text_len=len(text))
        
        # OGG/Opus header mínimo (1 segundo de silencio a 48kHz mono)
        # Esto es un placeholder - en producción usar audio real
        return self._generate_silence_ogg(duration_ms=1000)

    def _generate_silence_ogg(self, duration_ms: int = 1000) -> bytes:
        """Genera un archivo OGG/Opus válido con silencio."""
        # Opus header simplificado para 48kHz mono, 20ms frames
        # Esto es un placeholder muy básico
        sample_rate = 48000
        channels = 1
        frame_duration_ms = 20
        frame_size = int(sample_rate * frame_duration_ms / 1000)  # 960 samples
        num_frames = duration_ms // frame_duration_ms
        
        # OGG container + Opus header (simplificado)
        # En producción, usar pyogg o subprocess con opusenc
        return b"OGG_OPUS_MOCK_SILENCE_PLACEHOLDER"

    def is_available(self) -> bool:
        return True


class PiperTTS(TextToSpeech):
    """TTS usando Piper (local, CPU-friendly, voces es-CL)."""

    def __init__(
        self,
        model_path: str = "/models/piper/es_CL-carlfm-x_low.onnx",
        config_path: str = "/models/piper/es_CL-carlfm-x_low.onnx.json",
        speaker_id: int = 0,
    ):
        self.model_path = model_path
        self.config_path = config_path
        self.speaker_id = speaker_id
        self._piper_bin = "piper"  # Asumimos que está en PATH

    async def synthesize(self, text: str, language: str = "es-CL") -> Optional[bytes]:
        if not self.is_available():
            return None

        # Piper genera WAV, necesitamos convertir a OGG/Opus
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
            wav_path = wav_tmp.name
        ogg_path = wav_path.replace(".wav", ".ogg")

        try:
            # Ejecutar Piper
            cmd = [
                self._piper_bin,
                "--model", self.model_path,
                "--config", self.config_path,
                "--output_file", wav_path,
            ]
            if self.speaker_id is not None:
                cmd.extend(["--speaker", str(self.speaker_id)])

            # Pasar texto por stdin
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(input=text.encode("utf-8"))

            if process.returncode != 0:
                logger.error("piper_tts_error", stderr=stderr.decode()[:500])
                return None

            # Convertir WAV a OGG/Opus usando ffmpeg
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", wav_path,
                "-c:a", "libopus", "-b:a", "32k",
                "-application", "voip",
                ogg_path,
            ]
            ffmpeg_proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await ffmpeg_proc.communicate()

            if ffmpeg_proc.returncode != 0:
                logger.error("ffmpeg_conversion_error")
                return None

            # Leer OGG resultante
            with open(ogg_path, "rb") as f:
                ogg_bytes = f.read()

            logger.info("piper_tts_synthesized", text_len=len(text), ogg_size=len(ogg_bytes))
            return ogg_bytes

        except Exception as e:
            logger.exception("piper_tts_exception", error=str(e))
            return None
        finally:
            # Limpiar temporales
            for path in [wav_path, ogg_path]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass

    def is_available(self) -> bool:
        import shutil
        return (
            shutil.which(self._piper_bin) is not None
            and os.path.exists(self.model_path)
            and os.path.exists(self.config_path)
            and shutil.which("ffmpeg") is not None
        )


class HuggingFaceTTS(TextToSpeech):
    """TTS usando Hugging Face Inference API (gratuito con límites)."""

    def __init__(self, api_token: str, model_id: str = "coqui/tts-es-cl"):
        self.api_token = api_token
        self.model_id = model_id
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    async def synthesize(self, text: str, language: str = "es-CL") -> Optional[bytes]:
        import httpx

        headers = {"Authorization": f"Bearer {self.api_token}"}
        payload = {"inputs": text}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 200:
                    # HF retorna audio directamente (WAV usualmente)
                    audio_bytes = response.content
                    logger.info("hf_tts_synthesized", text_len=len(text), audio_size=len(audio_bytes))
                    
                    # Si es WAV, convertir a OGG/Opus
                    if audio_bytes.startswith(b"RIFF"):
                        return await self._wav_to_ogg(audio_bytes)
                    return audio_bytes
                elif response.status_code == 503:
                    await asyncio.sleep(10)
                    response = await client.post(self.api_url, headers=headers, json=payload)
                    if response.status_code == 200:
                        audio_bytes = response.content
                        if audio_bytes.startswith(b"RIFF"):
                            return await self._wav_to_ogg(audio_bytes)
                        return audio_bytes
                logger.warning("hf_tts_error", status=response.status_code, text=response.text[:200])
                return None
            except Exception as e:
                logger.exception("hf_tts_exception", error=str(e))
                return None

    async def _wav_to_ogg(self, wav_bytes: bytes) -> bytes:
        """Convierte WAV a OGG/Opus usando ffmpeg."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
            wav_tmp.write(wav_bytes)
            wav_path = wav_tmp.name
        ogg_path = wav_path.replace(".wav", ".ogg")

        try:
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", wav_path,
                "-c:a", "libopus", "-b:a", "32k",
                "-application", "voip",
                ogg_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if proc.returncode == 0:
                with open(ogg_path, "rb") as f:
                    return f.read()
            return wav_bytes  # Fallback: devolver WAV original
        finally:
            for path in [wav_path, ogg_path]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass

    def is_available(self) -> bool:
        return bool(self.api_token)


class BrowserTTS(TextToSpeech):
    """TTS usando Web Speech API del navegador (solo para frontend web)."""
    
    async def synthesize(self, text: str, language: str = "es-CL") -> Optional[bytes]:
        # No implementable en backend - solo para referencia
        logger.warning("browser_tts_not_available_in_backend")
        return None

    def is_available(self) -> bool:
        return False


# Factory para obtener instancia según configuración
def get_tts_provider() -> TextToSpeech:
    """Factory que retorna la instancia TTS según configuración."""
    provider = settings.tts_provider.lower()

    if provider == "piper":
        return PiperTTS()
    elif provider == "huggingface":
        return HuggingFaceTTS(api_token=settings.huggingface_api_token or "")
    else:
        return MockTTS()


# Función de conveniencia para usar en handlers
async def synthesize_speech(text: str, language: str = "es-CL") -> Optional[bytes]:
    """Sintetiza texto a audio usando el proveedor configurado."""
    provider = get_tts_provider()
    
    if not provider.is_available():
        logger.warning("tts_provider_unavailable", provider=settings.tts_provider)
        return None

    try:
        return await provider.synthesize(text, language)
    except Exception as e:
        logger.exception("tts_synthesize_error", provider=settings.tts_provider, error=str(e))
        return None