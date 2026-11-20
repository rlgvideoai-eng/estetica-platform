"""RAG Mock Server - FastAPI simple para desarrollo."""
import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Mock", version="0.1.0")

MOCK_RAG_PATH = Path(__file__).parent / "mock_rag.json"


class RAGQuery(BaseModel):
    query: str
    top_k: int = Field(default=4, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class RAGChunk(BaseModel):
    text: str
    source: str
    score: float


class RAGResponse(BaseModel):
    chunks: List[RAGChunk] = Field(default_factory=list)


def load_mock_rag() -> List[Dict]:
    """Carga el mock RAG desde archivo JSON."""
    try:
        if MOCK_RAG_PATH.exists():
            with open(MOCK_RAG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error cargando mock RAG: {e}")
    return []


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rag-mock", "version": "0.1.0"}


@app.post("/query", response_model=RAGResponse)
async def query_rag(query: RAGQuery):
    """Endpoint principal de consulta RAG."""
    mock_data = load_mock_rag()
    if not mock_data:
        # Fallback mínimo
        return RAGResponse(chunks=[
            RAGChunk(text="Ayudio es un centro de estética en Providencia, Santiago.", source="mock_default", score=0.8),
            RAGChunk(text="Horarios: Lunes a Viernes 9:00-19:00, Sábado 9:00-14:00.", source="mock_default", score=0.7),
        ])

    query_lower = query.query.lower()
    scored_chunks = []

    for entry in mock_data:
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

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for _, chunk in scored_chunks[:query.top_k]]

    logger.info(f"RAG query: '{query.query[:50]}' -> {len(top_chunks)} chunks")
    return RAGResponse(chunks=top_chunks)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)