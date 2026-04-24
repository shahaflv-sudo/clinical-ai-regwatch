"""Generate Gemini text-embedding-004 embeddings (768 dim)."""
from __future__ import annotations
import google.generativeai as genai

from .gemini_client import EMBED_MODEL, EMBED_DIM


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single piece of text. Truncates to model max."""
    text = (text or "").strip()
    if not text:
        return [0.0] * EMBED_DIM
    text = text[:8000]
    resp = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
        task_type=task_type,
        output_dimensionality=EMBED_DIM,
    )
    return resp["embedding"]


def embed_query(text: str) -> list[float]:
    return embed_text(text, task_type="RETRIEVAL_QUERY")
