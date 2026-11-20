"""Cliente RAG - Consulta a Databricks o mock local con cache y retry."""
import json
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings
from ..utils import get_logger
from .schemas import RAGChunk, RAGQuery, RAGResponse

logger = get_logger(__name__)

# Cache simple en memoria (TTL 10 min)
_cache: Dict[str, tuple[List[RAGChunk], float]] = {}
_CACHE_TTL = 600  # 10 minutos

# Mock local path
MOCK_RAG_PATH = Path(__file__).parent / "mock_rag.json"


class RAGClientError(Exception):
    """Error del cliente RAG."""
    pass


async def query_rag(
    query: str,
    top_k: int = 4,
    filters: Optional[Dict[str, Any]] = None,
) -> List[RAGChunk]:
    """Consulta al RAG con cache, retry y fallback a mock."""
    cache_key = f"{query}:{top_k}:{json.dumps(filters, sort_keys=True) if filters else ''}"

    # 1. Verificar cache
    if cache_key in _cache:
        chunks, timestamp = _cache[cache_key]
        if time.time() - timestamp < _CACHE_TTL:
            logger.debug("rag_cache_hit", query=query[:50])
            return chunks
        else:
            del _cache[cache_key]

    # 2. Intentar endpoint real (Databricks)
    if settings.databricks_rag_url and settings.databricks_rag_url != "http://rag-mock:8000":
        try:
            chunks = await _query_databricks_rag(query, top_k, filters)
            if chunks:
                _cache[cache_key] = (chunks, time.time())
                return chunks
        except Exception as e:
            logger.warning("databricks_rag_failed", error=str(e), query=query[:50])

    # 3. Fallback a mock local
    logger.info("rag_using_mock", query=query[:50])
    chunks = await _query_mock_rag(query, top_k, filters)
    _cache[cache_key] = (chunks, time.time())
    return chunks


async def _query_databricks_rag(
    query: str,
    top_k: int,
    filters: Optional[Dict[str, Any]],
) -> List[RAGChunk]:
    """Consulta al endpoint de Databricks (Model Serving / Vector Search)."""
    headers = {
        "Content-Type": "application/json",
    }
    if settings.databricks_token:
        headers["Authorization"] = f"Bearer {settings.databricks_token}"

    payload = {
        "query": query,
        "top_k": top_k,
    }
    if filters:
        payload["filters"] = filters

    timeout = httpx.Timeout(10.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Primer intento
        response = await client.post(
            f"{settings.databricks_rag_url}/query",
            json=payload,
            headers=headers,
        )

        if response.status_code == 200:
            data = response.json()
            return _parse_rag_response(data)

        # Reintento único si error 5xx
        if 500 <= response.status_code < 600:
            logger.warning("rag_retry", status=response.status_code)
            response = await client.post(
                f"{settings.databricks_rag_url}/query",
                json=payload,
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                return _parse_rag_response(data)

        raise RAGClientError(f"Databricks RAG error: {response.status_code} - {response.text}")


def _parse_rag_response(data: Dict) -> List[RAGChunk]:
    """Parsea respuesta del RAG - soporta ambos formatos."""
    chunks = []

    # Formato 1: chunks con text, source, score
    if "chunks" in data:
        for chunk_data in data["chunks"]:
            chunks.append(RAGChunk(
                text=chunk_data.get("text", ""),
                source=chunk_data.get("source", "unknown"),
                score=chunk_data.get("score", 0.0),
            ))
    # Formato 2: answer + sources (respuesta generada)
    elif "answer" in data and "sources" in data:
        chunks.append(RAGChunk(
            text=data["answer"],
            source="generated_answer",
            score=1.0,
        ))
        for src in data["sources"]:
            chunks.append(RAGChunk(
                text=src,
                source="source_reference",
                score=0.9,
            ))

    return chunks


async def _query_mock_rag(
    query: str,
    top_k: int,
    filters: Optional[Dict[str, Any]],
) -> List[RAGChunk]:
    """Consulta al mock local (archivo JSON)."""
    mock_data = _load_mock_rag()
    if not mock_data:
        # Mock mínimo por defecto
        return [
            RAGChunk(
                text="Ayudio es un centro de estética en Providencia, Santiago. Ofrecemos masajes, lavados, teñidos, uñas y más.",
                source="mock_default",
                score=0.8,
            ),
            RAGChunk(
                text="Horarios: Lunes a Viernes 9:00-19:00, Sábado 9:00-14:00. Cerrado domingos.",
                source="mock_default",
                score=0.7,
            ),
        ]

    # Búsqueda simple por palabras clave en mock
    query_lower = query.lower()
    scored_chunks = []

    for entry in mock_data:
        # Calcular score simple basado en coincidencia de palabras
        text_lower = entry.get("text", "").lower()
        keywords = query_lower.split()
        matches = sum(1 for kw in keywords if kw in text_lower)
        score = matches / len(keywords) if keywords else 0

        if score > 0:
            scored_chunks.append((
                score,
                RAGChunk(
                    text=entry.get("text", ""),
                    source=entry.get("source", "mock"),
                    score=score,
                )
            ))

    # Ordenar por score descendente y tomar top_k
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored_chunks[:top_k]]


@lru_cache(maxsize=1)
def _load_mock_rag() -> List[Dict]:
    """Carga el mock RAG desde archivo JSON (cacheado)."""
    try:
        if MOCK_RAG_PATH.exists():
            with open(MOCK_RAG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("mock_rag_load_error", error=str(e))
    return []


# Función para invalidar cache (útil para tests)
def invalidate_rag_cache() -> None:
    """Invalida todo el cache del RAG."""
    global _cache
    _cache.clear()
    logger.info("rag_cache_invalidated")