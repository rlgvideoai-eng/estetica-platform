"""Logging estructurado con structlog + correlation ID."""
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from ..config import settings

# Context variable para correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Obtiene o genera un correlation ID para la request actual."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    correlation_id_var.set(cid)


def clear_correlation_id() -> None:
    correlation_id_var.set("")


class CorrelationIDProcessor:
    """Procesador structlog que inyecta correlation_id en todos los logs."""

    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        cid = get_correlation_id()
        if cid:
            event_dict["correlation_id"] = cid
        return event_dict


def configure_logging() -> None:
    """Configura structlog con JSON o console según settings."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        CorrelationIDProcessor(),
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]

    if settings.log_format == "json":
        # JSON para producción / logs centralizados
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s %(correlation_id)s",
            rename_fields={"level": "severity", "timestamp": "timestamp"},
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(settings.log_level)

        structlog.configure(
            processors=shared_processors + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Console pretty para desarrollo
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Silenciar loggers ruidosos
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Obtiene un logger estructurado para el módulo dado."""
    return structlog.get_logger(name)