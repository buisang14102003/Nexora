from dataclasses import dataclass
from uuid import UUID

from qdrant_client.http import models as qdrant_models

from app.services.chunking import Chunk
from app.services.vector_store import QdrantVectorStore


WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000010")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000020")
SECOND_DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000021")


class FakeEmbeddings:
    def __init__(self) -> None:
        self.document_inputs: list[list[str]] = []
        self.query_inputs: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_inputs.append(texts)
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_inputs.append(text)
        return [0.1, 0.2, 0.3]


@dataclass
class FakeQueryResponse:
    points: list[object]


class FakeQdrant:
    def __init__(self) -> None:
        self.operations: list[tuple[str, object]] = []
        self.query_filter: qdrant_models.Filter | None = None
        self.points: list[qdrant_models.PointStruct] = []

    def collection_exists(self, _: str) -> bool:
        return False

    def create_collection(self, **kwargs: object) -> None:
        self.operations.append(("create_collection", kwargs))

    def create_payload_index(self, **kwargs: object) -> None:
        self.operations.append(("create_payload_index", kwargs))

    def upsert(self, *, points: list[qdrant_models.PointStruct], **_: object) -> None:
        self.operations.append(("upsert", points))
        self.points = points

    def query_points(
        self, *, query_filter: qdrant_models.Filter, **_: object
    ) -> FakeQueryResponse:
        self.query_filter = query_filter
        return FakeQueryResponse(points=[])


def _chunk() -> Chunk:
    return Chunk(
        id=UUID("00000000-0000-0000-0000-000000000030"),
        document_id=DOCUMENT_ID,
        page_number=2,
        text="Local-only workspace content",
        source_name="policy.pdf",
        source_type="pdf",
        start_offset=10,
        end_offset=38,
    )


def test_index_creates_filter_indexes_before_upsert_and_preserves_payload() -> None:
    client = FakeQdrant()
    embeddings = FakeEmbeddings()
    store = QdrantVectorStore(client=client, embeddings=embeddings)

    store.index_chunks(WORKSPACE_ID, DOCUMENT_ID, [_chunk()])

    assert [operation for operation, _ in client.operations] == [
        "create_collection",
        "create_payload_index",
        "create_payload_index",
        "upsert",
    ]
    index_fields = [
        kwargs["field_name"]
        for operation, kwargs in client.operations
        if operation == "create_payload_index"
    ]
    assert index_fields == ["workspace_id", "document_id"]
    assert client.points[0].payload == {
        "workspace_id": str(WORKSPACE_ID),
        "document_id": str(DOCUMENT_ID),
        "chunk_id": str(_chunk().id),
        "source_name": "policy.pdf",
        "source_type": "pdf",
        "page_number": 2,
        "text": "Local-only workspace content",
    }
    assert embeddings.document_inputs == [["Local-only workspace content"]]


def test_qdrant_search_always_filters_workspace_with_exact_match() -> None:
    client = FakeQdrant()
    embeddings = FakeEmbeddings()
    store = QdrantVectorStore(client=client, embeddings=embeddings)

    store.search("question", workspace_id=WORKSPACE_ID)

    assert client.query_filter is not None
    assert client.query_filter.must == [
        qdrant_models.FieldCondition(
            key="workspace_id",
            match=qdrant_models.MatchValue(value=str(WORKSPACE_ID)),
        )
    ]
    assert embeddings.query_inputs == ["question"]


def test_search_adds_document_filter_without_dropping_workspace_filter() -> None:
    client = FakeQdrant()
    store = QdrantVectorStore(client=client, embeddings=FakeEmbeddings())

    store.search("question", workspace_id=WORKSPACE_ID, document_id=DOCUMENT_ID)

    assert client.query_filter is not None
    assert [condition.key for condition in client.query_filter.must] == [
        "workspace_id",
        "document_id",
    ]


def test_search_filters_multiple_selected_documents_before_top_k() -> None:
    client = FakeQdrant()
    store = QdrantVectorStore(client=client, embeddings=FakeEmbeddings())

    store.search(
        "question",
        workspace_id=WORKSPACE_ID,
        document_ids=[DOCUMENT_ID, SECOND_DOCUMENT_ID],
    )

    assert client.query_filter is not None
    assert client.query_filter.must[1] == qdrant_models.FieldCondition(
        key="document_id",
        match=qdrant_models.MatchAny(any=[str(DOCUMENT_ID), str(SECOND_DOCUMENT_ID)]),
    )
