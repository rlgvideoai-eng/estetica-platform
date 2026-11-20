"""Voice Mock Server - STT/TTS mocks para desarrollo."""
import asyncio
import logging
import random
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Mock", version="0.1.0")


class STTResponse(BaseModel):
    text: str
    language: str = "es-CL"
    confidence: float = 0.95


class TTSRequest(BaseModel):
    text: str
    language: str = "es-CL"
    voice: Optional[str] = None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "voice-mock", "version": "0.1.0"}


# ============================================================
# STT - Speech to Text (Mock)
# ============================================================

@app.post("/stt/transcribe", response_model=STTResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(default="es-CL"),
):
    """Mock STT - Simula transcripción de audio."""
    # Simular tiempo de procesamiento
    await asyncio.sleep(0.5)

    # Leer archivo para obtener tamaño (simular variación)
    content = await file.read()
    size_kb = len(content) / 1024

    # Mock responses basados en tamaño
    mock_transcriptions = [
        "Hola, quiero agendar una hora para un masaje",
        "Quiero un masaje relajante para mañana en la mañana",
        "Hola, me gustaría reservar un masaje descontracturante para el viernes a las tres de la tarde con María",
        "Quiero agendar un lavado con hidratación para el martes",
        "Necesito cancelar mi reserva del jueves",
        "¿Cuánto cuesta el esmaltado semipermanente?",
        "¿A qué hora abren los sábados?",
    ]

    # Seleccionar basado en tamaño (simulando duración)
    if size_kb < 10:
        text = "Hola"
    elif size_kb < 30:
        text = random.choice(mock_transcriptions[:3])
    else:
        text = random.choice(mock_transcriptions)

    logger.info(f"STT mock: {file.filename} ({size_kb:.1f}KB) -> '{text}'")

    return STTResponse(
        text=text,
        language=language,
        confidence=round(random.uniform(0.85, 0.98), 2),
    )


# ============================================================
# TTS - Text to Speech (Mock)
# ============================================================

@app.post("/tts/synthesize")
async def synthesize_speech(request: TTSRequest):
    """Mock TTS - Genera audio OGG/Opus falso."""
    # Simular tiempo de procesamiento
    await asyncio.sleep(0.3)

    logger.info(f"TTS mock: '{request.text[:50]}' ({request.language})")

    # Generar OGG/Opus mínimo válido (silencio de 1 segundo)
    # En producción esto sería audio real
    ogg_bytes = _generate_mock_ogg()

    return Response(
        content=ogg_bytes,
        media_type="audio/ogg",
        headers={
            "Content-Disposition": 'attachment; filename="speech.ogg"',
            "X-TTS-Mock": "true",
        },
    )


def _generate_mock_ogg(duration_ms: int = 1000) -> bytes:
    """Genera un archivo OGG/Opus mínimo válido (silencio)."""
    # OGG container header + Opus head + tags + audio data (simplificado)
    # Esto es un placeholder - en producción usar pyogg o subprocess con opusenc
    return (
        b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00"
        b"OpusHead\x01\x00\x01\x00\x80\xbb\x00\x00\x00\x00\x00\x00\x00\x00"
        b"OpusTags\x00\x00\x00\x00\x08AyudioTTS\x00\x00\x00\x00"
        b"OggS\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00" * 100  # Datos de audio (silencio placeholder)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)