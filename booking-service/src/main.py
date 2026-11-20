"""Booking Service - FastAPI entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .utils.logging import configure_logging, get_logger, get_correlation_id, set_correlation_id, clear_correlation_id
from .db.session import init_db, close_db, get_session_factory
from .services.scheduler_service import get_scheduler_service
from .api.routes import services, availability, bookings, clients, admin

# Configurar logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    # Startup
    logger.info("starting_booking_service", version="0.1.0")
    await init_db()
    logger.info("database_initialized")

    # Iniciar scheduler de recordatorios
    session_factory = get_session_factory()
    scheduler = await get_scheduler_service(session_factory)
    await scheduler.start()
    logger.info("scheduler_started")

    yield

    # Shutdown
    logger.info("shutting_down_booking_service")
    await scheduler.shutdown()
    await close_db()
    logger.info("booking_service_stopped")


app = FastAPI(
    title="Ayudio Booking Service",
    description="Servicio de agendamiento para centro de estética Ayudio",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.log_level == "DEBUG" else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Middleware para correlation ID y logging."""
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
        logger.info("http_request_end", status_code=response.status_code)
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
        "service": "booking-service",
        "version": "0.1.0",
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check - verifica DB."""
    checks = {"database": "unknown"}

    try:
        from .db.session import get_session
        async with get_session() as session:
            await session.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
        },
    )


# Registrar rutas
app.include_router(services.router)
app.include_router(availability.router)
app.include_router(bookings.router)
app.include_router(clients.router)
app.include_router(admin.router, prefix="/admin", tags=["admin"])


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