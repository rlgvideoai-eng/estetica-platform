"""Bot Service - FastAPI entry point with multi-channel support."""
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .utils import configure_logging, get_logger
from .channels.factory import initialize_all_channels, shutdown_all_channels
from .utils.logging import get_correlation_id, set_correlation_id, clear_correlation_id
from .bot.handler import setup_bot, bot_application
from .utils.logging import get_correlation_id, set_correlation_id, clear_correlation_id

# Configurar logging al importar
configure_logging()
logger = get_logger(__name__)

# Canales activos
active_channels: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación con multi-canal."""
    # Startup
    logger.info("starting_bot_service", version="0.1.0", environment="development")

    # Inicializar todos los canales configurados
    global active_channels
    active_channels = await initialize_all_channels()
    logger.info("all_channels_initialized", channels=list(active_channels.keys()))

    yield

    # Shutdown
    logger.info("shutting_down_bot_service")
    await shutdown_all_channels(active_channels)
    logger.info("bot_service_stopped")


app = FastAPI(
    title="Ayudio Bot Service",
    description="Servicio de bot multi-canal (Telegram + WhatsApp) para centro de estética Ayudio",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.log_level == "DEBUG" else None,
    redoc_url=None,
)

# CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Middleware para correlation ID y logging de requests."""
    # Generar o extraer correlation ID
    cid = request.headers.get("X-Correlation-ID") or f"req-{id(request)}"
    set_correlation_id(cid)

    logger = get_logger("http")
    logger.info(
        "http_request_start",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_host=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = get_correlation_id()
        logger.info(
            "http_request_end",
            status_code=response.status_code,
        )
        return response
    except Exception as e:
        logger.exception("http_request_error", error=str(e))
        raise
    finally:
        clear_correlation_id()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "bot-service",
        "version": "0.1.0",
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check - verifica conexiones críticas."""
    checks = {
        "telegram_bot": "ok",
        "booking_service": "unknown",
        "rag_service": "unknown",
    }

    # Verificar booking service
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.booking_service_url}/health")
            checks["booking_service"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception:
        checks["booking_service"] = "unreachable"

    # Verificar RAG service
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.databricks_rag_url}/health")
            checks["rag_service"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception:
        checks["rag_service"] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
        },
    )


# ============================================================
# WEBHOOKS MULTI-CANAL
# ============================================================

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Webhook para recibir actualizaciones de Telegram."""
    from .channels.factory import get_channel_adapter, ChannelType
    
    try:
        adapter = get_channel_adapter(ChannelType.TELEGRAM)
        body = await request.body()
        
        # Verificar firma si hay secret
        signature = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not adapter.verify_webhook_signature(body, signature):
            return JSONResponse(status_code=401, content={"error": "Invalid signature"})
        
        import json
        update_data = json.loads(body)
        message = await adapter.process_update(update_data)
        
        if message:
            # Procesar mensaje a través del handler existente
            from .bot.handler import handle_callback_query, handle_text_message, handle_voice_message
            # Crear mock update/context para compatibilidad
            # En producción, se debería refactorizar para usar ChannelAdapter directamente
            pass
        
        return {"status": "ok"}
    except Exception as e:
        logger.exception("telegram_webhook_error", error=str(e))
        return JSONResponse(status_code=500, content={"error": "webhook_error"})


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Webhook para recibir actualizaciones de WhatsApp (Meta Cloud API)."""
    from .channels.factory import get_channel_adapter, ChannelType
    
    try:
        adapter = get_channel_adapter(ChannelType.WHATSAPP)
        body = await request.body()
        
        # Verificar firma X-Hub-Signature-256
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not adapter.verify_webhook_signature(await request.body(), signature):
            return JSONResponse(status_code=401, content={"error": "Invalid signature"})
        
        import json
        update_data = json.loads(body)
        
        # Verificar challenge de verificación (primer webhook)
        if "hub.challenge" in str(update_data):
            challenge = update_data.get("hub.challenge")
            return Response(content=challenge, media_type="text/plain")
        
        message = await adapter.process_update(update_data)
        
        if message:
            # Procesar mensaje a través del agente
            from .bot.handler import _delegate_to_agent
            from .agent.core import run_agent_turn
            
            # En un caso real, se usaría el ChannelAdapter para enviar respuestas
            # Por ahora, logueamos
            logger.info("whatsapp_message_received", 
                       user_id=message.user.id, 
                       text=message.text[:50] if message.text else "voice")
        
        return {"status": "ok"}
    except Exception as e:
        logger.exception("whatsapp_webhook_error", error=str(e))
        return JSONResponse(status_code=500, content={"error": "webhook_error"})


@app.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    """Verificación de webhook de WhatsApp (GET challenge)."""
    from .channels.factory import get_channel_adapter, ChannelType
    
    try:
        adapter = get_channel_adapter(ChannelType.WHATSAPP)
        
        # Verificar token de verificación
        verify_token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        mode = request.query_params.get("hub.mode")
        
        if mode == "subscribe" and challenge:
            if verify_token == (settings.whatsapp_webhook_verify_token or "ayudio_webhook_verify"):
                return Response(content=challenge, media_type="text/plain")
        
        return JSONResponse(status_code=403, content={"error": "Verification failed"})
    except Exception as e:
        logger.exception("whatsapp_verify_error", error=str(e))
        return JSONResponse(status_code=500, content={"error": "verification_error"})


# Rutas existentes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "bot-service",
        "version": "0.1.0",
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check - verifica conexiones críticas."""
    checks = {
        "telegram_bot": "ok",
        "whatsapp": "ok" if getattr(settings, "whatsapp_access_token", None) else "not_configured",
        "booking_service": "unknown",
        "rag_service": "unknown",
    }

    # Verificar booking service
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.booking_service_url}/health")
            checks["booking_service"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception:
        checks["booking_service"] = "unreachable"

    # Verificar RAG service
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.databricks_rag_url}/health")
            checks["rag_service"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception:
        checks["rag_service"] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
        },
    )


# Webhook legacy Telegram (para compatibilidad)
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Endpoint legacy para webhooks de Telegram (modo webhook alternativo)."""
    logger.warning("webhook_received_but_using_polling")
    return {"status": "ok", "mode": "polling"}


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Error interno del servidor",
            "correlation_id": get_correlation_id(),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )