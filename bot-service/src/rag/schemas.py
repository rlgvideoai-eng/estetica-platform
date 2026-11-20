"""Esquemas Pydantic para RAG."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RAGQuery(BaseModel):
    query: str = Field(..., description="Pregunta en lenguaje natural")
    top_k: int = Field(default=4, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class RAGChunk(BaseModel):
    text: str = Field(..., description="Texto del fragmento")
    source: str = Field(..., description="Fuente/origen del fragmento")
    score: float = Field(..., description="Score de relevancia 0-1")


class RAGResponse(BaseModel):
    chunks: List[RAGChunk] = Field(default_factory=list)
    # Formato alternativo: respuesta generada
    answer: Optional[str] = None
    sources: Optional[List[str]] = None