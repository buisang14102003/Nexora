"""Local-only, redacted trace metadata for RAG operations."""

from __future__ import annotations

from contextlib import AbstractContextManager
from hashlib import sha256
from time import perf_counter
from typing import Any

from app.core.config import get_settings


_SAFE_METADATA_KEYS = {
    "route",
    "model_id",
    "chat_model",
    "embedding_model",
    "chunk_ids",
    "status",
}
_PROTECTED_KEY_PARTS = ("prompt", "question", "document", "csv", "row", "text", "value")


class GraphTrace(AbstractContextManager["GraphTrace"]):
    """A trace payload that never retains raw user or document content."""

    def __init__(self, name: str, metadata: dict[str, str]) -> None:
        self.name = name
        self.metadata = _redacted_metadata(metadata)
        self._started_at = perf_counter()

    def set_status(self, status: str) -> None:
        self.metadata["status"] = status

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        self.metadata["latency_ms"] = str(round((perf_counter() - self._started_at) * 1000))
        if exc is not None:
            self.metadata["status"] = "error"
        else:
            self.metadata.setdefault("status", "ok")
        _send_to_local_langfuse(self.name, self.metadata)
        return False


def trace_graph_run(name: str, metadata: dict[str, str]) -> GraphTrace:
    """Create a redacted trace context suitable for a local Langfuse exporter.

    The caller may only observe routing and model metadata. Raw questions, document
    contents, and CSV rows are deliberately excluded before a trace leaves the app.
    """

    return GraphTrace(name, metadata)


def _redacted_metadata(metadata: dict[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in metadata.items():
        normalized_key = key.lower()
        if any(part in normalized_key for part in _PROTECTED_KEY_PARTS):
            continue
        if key == "workspace_id":
            safe["workspace_id_hash"] = sha256(str(value).encode()).hexdigest()[:16]
        elif key in _SAFE_METADATA_KEYS:
            safe[key] = str(value)
    return safe


def _send_to_local_langfuse(name: str, metadata: dict[str, str]) -> None:
    """Best-effort export; tracing must never prevent a local RAG answer."""

    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return
    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        trace = client.start_span(name=name, metadata=metadata)
        trace.update(metadata=metadata)
        trace.end()
        client.flush()
    except Exception:
        # Observability is optional for the MVP and must not expose failure details.
        return
