from collections.abc import Sequence
from typing import Any, Protocol
from uuid import UUID

from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.core.config import get_settings
from app.services.chunking import Chunk


class VectorStoreError(RuntimeError):
    """Raised when local embedding or vector indexing fails."""


class Embeddings(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class QdrantVectorStore:
    def __init__(
        self,
        client: QdrantClient | Any | None = None,
        embeddings: Embeddings | None = None,
        collection_name: str | None = None,
    ) -> None:
        settings = get_settings() if client is None or embeddings is None else None
        self.client = client or QdrantClient(url=settings.qdrant_url)
        self.embeddings = embeddings or OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
        self.collection_name = collection_name or (
            settings.qdrant_collection if settings is not None else "document_chunks"
        )

    def index_chunks(
        self,
        workspace_id: UUID,
        document_id: UUID,
        chunks: Sequence[Chunk],
    ) -> None:
        if not chunks:
            return
        try:
            vectors = self.embeddings.embed_documents([chunk.text for chunk in chunks])
            if len(vectors) != len(chunks) or not vectors or not vectors[0]:
                raise VectorStoreError("Embedding response did not match input chunks")
            self._ensure_collection(len(vectors[0]))
            points = [
                qdrant_models.PointStruct(
                    id=str(chunk.id),
                    vector=vector,
                    payload={
                        "workspace_id": str(workspace_id),
                        "document_id": str(document_id),
                        "chunk_id": str(chunk.id),
                        "source_name": chunk.source_name,
                        "source_type": chunk.source_type,
                        "page_number": chunk.page_number,
                        "text": chunk.text,
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
        except VectorStoreError:
            raise
        except Exception as error:
            raise VectorStoreError("Local vector indexing failed") from error

    def search(
        self,
        query: str,
        *,
        workspace_id: UUID,
        document_id: UUID | None = None,
        limit: int = 5,
    ) -> list[Any]:
        conditions = [
            qdrant_models.FieldCondition(
                key="workspace_id",
                match=qdrant_models.MatchValue(value=str(workspace_id)),
            )
        ]
        if document_id is not None:
            conditions.append(
                qdrant_models.FieldCondition(
                    key="document_id",
                    match=qdrant_models.MatchValue(value=str(document_id)),
                )
            )
        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=self.embeddings.embed_query(query),
                query_filter=qdrant_models.Filter(must=conditions),
                limit=limit,
                with_payload=True,
            )
        except Exception as error:
            raise VectorStoreError("Local vector search failed") from error
        return list(response.points)

    def _ensure_collection(self, vector_size: int) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
        for field_name in ("workspace_id", "document_id"):
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
                wait=True,
            )


def index_chunks(
    workspace_id: UUID,
    document_id: UUID,
    chunks: list[Chunk],
) -> None:
    QdrantVectorStore().index_chunks(workspace_id, document_id, chunks)
