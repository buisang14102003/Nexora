# Local Workspace RAG MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a local-only, multi-workspace RAG web MVP that ingests PDF/DOCX/CSV files, answers and summarizes in Vietnamese or English with citations, performs safe CSV calculations, and records redacted local Langfuse traces.

**Architecture:** Chainlit is a separate UI service that calls FastAPI. FastAPI owns authentication, workspace authorization, APIs, and LangGraph invocation; a separate Python worker claims durable ingestion jobs. PostgreSQL stores transactional data, MinIO stores uploaded originals, Qdrant stores workspace-filtered vector chunks, Ollama runs natively on the Mac, and Langfuse is self-hosted in Docker Compose.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Chainlit, LangChain, LangGraph, Qdrant, MinIO, Ollama, Langfuse, Docker Compose, pytest.

## Global Constraints

- Target is a Mac mini M4 with 16 GB unified RAM and 256 GB SSD.
- All documents, prompts, embeddings, inference, vector data, and traces stay on the local machine or private network.
- MVP supports `.csv`, `.docx`, text PDFs, scanned PDFs, and image uploads; legacy `.doc`, Google Docs, and cloud APIs are excluded.
- Users authenticate by email/password; only `admin` and `member` roles exist.
- Every resource and Qdrant query is scoped by `workspace_id`; cross-workspace access must fail.
- Answers must include citations or explicitly state that evidence was insufficient.
- CSV calculations use a validated operation schema and never execute arbitrary LLM-generated Python, SQL, or shell commands.
- Default models are Ollama `gemma3:4b` and `qwen3-embedding:0.6b`; model IDs remain environment configuration.
- Langfuse traces redact raw prompts, document text, and CSV rows by default.

---

## Planned file structure

```text
Ai-RAG/
├── compose.yaml
├── .env.example
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── app/
│   ├── api/{deps.py,main.py,routers/auth.py,routers/workspaces.py,routers/documents.py,routers/chat.py}
│   ├── core/{config.py,security.py,errors.py,observability.py}
│   ├── db/{base.py,session.py,models.py}
│   ├── schemas/{auth.py,workspace.py,document.py,chat.py}
│   ├── services/{auth.py,workspaces.py,storage.py,jobs.py,parsers.py,chunking.py,vector_store.py,citations.py,csv_analysis.py}
│   └── rag/{graph.py,nodes.py,prompts.py}
├── worker/main.py
├── chainlit_app.py
├── tests/{conftest.py,api/,services/,rag/,e2e/}
└── scripts/{pull_models.sh,seed_eval_data.py}
```

## Task 1: Bootstrap local runtime and test foundation

**Files:**
- Create: `pyproject.toml`, `.env.example`, `compose.yaml`, `app/core/config.py`, `app/api/main.py`, `worker/main.py`, `chainlit_app.py`, `tests/conftest.py`, `tests/test_health.py`, `scripts/pull_models.sh`, `scripts/validate_env.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces `Settings` from `app.core.config` and `app` from `app.api.main`.
- Produces `GET /healthz` returning `{"status":"ok"}`.
- Later tasks consume `get_settings()` and the Docker service hostnames in `.env`.

- [ ] **Step 1: Write the failing health test.**

```python
# tests/test_health.py
from fastapi.testclient import TestClient
from app.api.main import app


def test_healthz_returns_ok() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test to verify it fails.**

Run: `pytest tests/test_health.py -v`

Expected: FAIL because `app.api.main` does not exist.

- [ ] **Step 3: Add the minimum application configuration and health endpoint.**

```python
# app/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    minio_endpoint: str = "minio:9000"
    qdrant_url: str = "http://qdrant:6333"
    ollama_base_url: str = "http://host.docker.internal:11434"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    chat_model: str = "gemma3:4b"
    embedding_model: str = "qwen3-embedding:0.6b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# app/api/main.py
from fastapi import FastAPI

app = FastAPI(title="Local Workspace RAG")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

`compose.yaml` must define `postgres`, `minio`, `qdrant`, `api`, `worker`, `chainlit`, and the self-hosted Langfuse stack. It must mount named volumes for PostgreSQL, MinIO, Qdrant, and Langfuse data; bind application ports only to `127.0.0.1`; and set `OLLAMA_BASE_URL=http://host.docker.internal:11434` for API and worker. Task 1 creates minimal `worker/main.py` and `chainlit_app.py` entry points that start successfully; Task 5 and Task 8 replace them with their functional behavior. `.env.example` lists every secret key without a value, and `scripts/validate_env.py` fails with the names of missing required variables before `docker compose up` is run. `scripts/pull_models.sh` runs `ollama pull gemma3:4b` and `ollama pull qwen3-embedding:0.6b`.

- [ ] **Step 4: Run the focused test and container validation.**

Run: `pytest tests/test_health.py -v && docker compose config`

Expected: one passing test and a rendered Compose configuration with no unset required variables.

- [ ] **Step 5: Commit the foundation.**

```bash
git add pyproject.toml .env.example compose.yaml app tests scripts .gitignore
git commit -m "chore: bootstrap local RAG runtime"
```

## Task 2: Persist users, workspaces, and membership roles

**Files:**
- Create: `app/db/{base.py,session.py,models.py}`, `alembic/env.py`, `alembic/versions/001_initial_domain.py`, `app/schemas/{auth.py,workspace.py}`, `app/core/{security.py,errors.py}`, `app/services/{auth.py,workspaces.py}`, `tests/services/test_auth.py`, `tests/services/test_workspaces.py`
- Modify: `alembic.ini`, `app/core/config.py`

**Interfaces:**
- Consumes `Settings.database_url`.
- Produces SQLAlchemy models `User`, `Workspace`, and `Membership`.
- Produces `hash_password(password: str) -> str`, `verify_password(password: str, password_hash: str) -> bool`, and `require_role(membership: Membership, allowed: set[str]) -> None`.

- [ ] **Step 1: Write failing password and membership tests.**

```python
def test_password_hash_never_equals_plaintext() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)


def test_member_cannot_be_treated_as_admin(member_membership) -> None:
    with pytest.raises(ForbiddenError):
        require_role(member_membership, {"admin"})
```

- [ ] **Step 2: Run the tests to verify failure.**

Run: `pytest tests/services/test_auth.py tests/services/test_workspaces.py -v`

Expected: FAIL because the security and workspace services do not exist.

- [ ] **Step 3: Implement the data model and minimum services.**

```python
class MembershipRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    role: Mapped[MembershipRole] = mapped_column(nullable=False)
```

```python
# app/core/errors.py
class ForbiddenError(Exception):
    pass
```

Use Argon2 through `pwdlib.PasswordHash.recommended()` for password hashes. The migration creates UUID primary keys, unique user email, unique workspace slug, unique membership pairs, and timestamps. `require_role` raises `ForbiddenError` for a role outside the allowed set. `create_workspace(session, owner_id, name)` inserts the workspace and an admin membership in one transaction.

- [ ] **Step 4: Run tests and migration.**

Run: `alembic upgrade head && pytest tests/services/test_auth.py tests/services/test_workspaces.py -v`

Expected: migration completes and tests pass.

- [ ] **Step 5: Commit the domain layer.**

```bash
git add app/db app/core/security.py app/core/errors.py app/services app/schemas alembic tests/services alembic.ini
git commit -m "feat: add users workspaces and membership roles"
```

## Task 3: Expose authenticated FastAPI workspace APIs

**Files:**
- Create: `app/api/deps.py`, `app/api/routers/{auth.py,workspaces.py}`, `tests/api/{test_auth.py,test_workspaces.py}`
- Modify: `app/api/main.py`, `app/schemas/auth.py`, `app/schemas/workspace.py`

**Interfaces:**
- Consumes `User`, `Workspace`, `Membership`, `hash_password`, and `create_workspace`.
- Produces `POST /auth/register`, `POST /auth/login`, `POST /workspaces`, `GET /workspaces`, and `POST /workspaces/{workspace_id}/members`.
- Produces `get_current_user()` and `require_workspace_membership(workspace_id, user)` dependencies.

- [ ] **Step 1: Write failing API isolation tests.**

```python
def test_member_cannot_add_workspace_members(client, member_token, workspace_id) -> None:
    response = client.post(
        f"/workspaces/{workspace_id}/members",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"email": "new@example.test", "role": "member"},
    )
    assert response.status_code == 403


def test_user_cannot_list_another_users_workspace(client, other_token, workspace_id) -> None:
    response = client.get(
        f"/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Run API tests to verify failure.**

Run: `pytest tests/api/test_auth.py tests/api/test_workspaces.py -v`

Expected: FAIL because routers and dependencies are not registered.

- [ ] **Step 3: Implement JWT dependencies and routers.**

```python
def require_workspace_membership(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Membership:
    membership = session.get(Membership, {"user_id": user.id, "workspace_id": workspace_id})
    if membership is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return membership
```

`POST /auth/register` creates a user with a password hash. `POST /auth/login` returns a signed bearer token containing only user ID and expiry. All workspace routes use `require_workspace_membership`; admin-only routes call `require_role(membership, {"admin"})`.

- [ ] **Step 4: Run API tests.**

Run: `pytest tests/api/test_auth.py tests/api/test_workspaces.py -v`

Expected: PASS; membership violations return no resource details.

- [ ] **Step 5: Commit the API slice.**

```bash
git add app/api app/schemas tests/api
git commit -m "feat: add authenticated workspace APIs"
```

## Task 4: Add durable uploads, document records, and ingestion jobs

**Files:**
- Create: `app/schemas/document.py`, `app/services/{storage.py,jobs.py}`, `app/api/routers/documents.py`, `tests/api/test_documents.py`, `tests/services/test_jobs.py`
- Modify: `app/db/models.py`, `alembic/versions/002_documents_and_jobs.py`, `app/api/main.py`

**Interfaces:**
- Produces models `Document` and `IngestionJob` with statuses `queued`, `processing`, `ready`, and `failed`.
- Produces `store_upload(workspace_id: UUID, file: UploadFile) -> Document` and `claim_next_job(session: Session) -> IngestionJob | None`.
- Produces `POST /workspaces/{workspace_id}/documents` and `GET /workspaces/{workspace_id}/documents`.

- [ ] **Step 1: Write failing upload and job claim tests.**

```python
def test_upload_creates_queued_job(client, admin_token, workspace_id, sample_docx) -> None:
    response = client.post(
        f"/workspaces/{workspace_id}/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("guide.docx", sample_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_claimed_job_is_not_claimed_twice(session) -> None:
    first = claim_next_job(session)
    second = claim_next_job(session)
    assert first is not None
    assert second is None
```

- [ ] **Step 2: Run the tests to verify failure.**

Run: `pytest tests/api/test_documents.py tests/services/test_jobs.py -v`

Expected: FAIL because document upload and job services do not exist.

- [ ] **Step 3: Implement safe upload and durable job claiming.**

`Document` stores `workspace_id`, original filename, MIME type, MinIO object key, source type, status, and timestamps. `IngestionJob` stores `document_id`, status, attempts, safe error message, and claimed time. Validate extension, MIME type, and configured upload size before MinIO write. `claim_next_job` must atomically choose one queued job with `FOR UPDATE SKIP LOCKED`, mark it `processing`, and increment attempts.

- [ ] **Step 4: Run migration and focused tests.**

Run: `alembic upgrade head && pytest tests/api/test_documents.py tests/services/test_jobs.py -v`

Expected: PASS; a member from a different workspace receives 404 on list and upload attempts.

- [ ] **Step 5: Commit document job creation.**

```bash
git add app/db/models.py app/schemas/document.py app/services app/api/routers/documents.py alembic tests
git commit -m "feat: add workspace document uploads and jobs"
```

## Task 5: Implement extraction, OCR fallback, chunking, embeddings, and Qdrant indexing

**Files:**
- Create: `app/services/{parsers.py,chunking.py,vector_store.py}`, `worker/main.py`, `tests/services/{test_parsers.py,test_chunking.py,test_vector_store.py}`
- Modify: `app/services/jobs.py`, `app/db/models.py`, `compose.yaml`

**Interfaces:**
- Produces `ExtractedPage(page_number: int, text: str)`, `extract_document(document: Document) -> list[ExtractedPage]`, and `chunk_pages(pages: list[ExtractedPage], document_id: UUID) -> list[Chunk]`.
- Produces `index_chunks(workspace_id: UUID, document_id: UUID, chunks: list[Chunk]) -> None`.
- Worker consumes `claim_next_job` and produces `ready`/`failed` document and job states.

- [ ] **Step 1: Write failing parser, metadata, and workspace-filter tests.**

```python
def test_pdf_chunk_retains_page_and_workspace_metadata(sample_pdf) -> None:
    pages = extract_document(sample_pdf)
    chunks = chunk_pages(pages, document_id=UUID("00000000-0000-0000-0000-000000000001"))
    assert chunks[0].page_number == 1
    assert chunks[0].text


def test_qdrant_search_always_filters_workspace(fake_qdrant) -> None:
    store = QdrantVectorStore(fake_qdrant)
    store.search("question", workspace_id=WORKSPACE_ID)
    assert fake_qdrant.last_filter == {"workspace_id": str(WORKSPACE_ID)}
```

- [ ] **Step 2: Run tests to verify failure.**

Run: `pytest tests/services/test_parsers.py tests/services/test_chunking.py tests/services/test_vector_store.py -v`

Expected: FAIL because extraction and vector services do not exist.

- [ ] **Step 3: Implement local ingestion.**

Use `python-docx` for DOCX paragraphs/tables and `pypdf` for page-aware PDF extraction. If extracted PDF page text is blank, render that page locally and run Tesseract OCR; store the returned page number. Use `pandas` only to inspect CSV headers/types and preserve it for the CSV tool. Chunk prose at a configurable token-aware size with overlap, retaining page number, source name, and offsets.

Qdrant upserts must use payload:

```python
{
    "workspace_id": str(workspace_id),
    "document_id": str(document_id),
    "chunk_id": str(chunk.id),
    "source_name": chunk.source_name,
    "source_type": chunk.source_type,
    "page_number": chunk.page_number,
    "text": chunk.text,
}
```

Create payload indexes for `workspace_id` and `document_id` before indexing. Use Ollama's embedding endpoint through LangChain and use the same configured model during index and query.

- [ ] **Step 4: Run worker-backed integration tests.**

Run: `pytest tests/services/test_parsers.py tests/services/test_chunking.py tests/services/test_vector_store.py -v`

Expected: PASS; DOCX, text PDF, scanned fixture, and CSV create expected document states or safe failures.

- [ ] **Step 5: Commit the ingestion pipeline.**

```bash
git add app/services worker tests compose.yaml
git commit -m "feat: index local documents with OCR and Qdrant"
```

## Task 6: Build cited LangGraph RAG and summary routes

**Files:**
- Create: `app/rag/{graph.py,nodes.py,prompts.py}`, `app/services/citations.py`, `app/schemas/chat.py`, `app/api/routers/chat.py`, `tests/rag/{test_graph.py,test_citations.py}`, `tests/api/test_chat.py`
- Modify: `app/api/main.py`, `app/db/models.py`, `alembic/versions/003_chats_and_citations.py`

**Interfaces:**
- Produces `run_chat(workspace_id: UUID, user_id: UUID, question: str, document_ids: list[UUID] | None) -> ChatResult`.
- Produces `Citation(document_id: UUID, source_name: str, page_number: int | None, row_range: str | None, chunk_id: UUID | None)`.
- Produces `POST /workspaces/{workspace_id}/chat` streaming answer events and a final citation event.

- [ ] **Step 1: Write failing graph behavior tests.**

```python
def test_graph_returns_insufficient_evidence_without_retrieved_chunks() -> None:
    result = run_graph_for_test(question="Who is the CEO?", retrieved_chunks=[])
    assert result.answer == "I could not find that information in this workspace's documents."
    assert result.citations == []


def test_answer_citation_references_retrieved_page() -> None:
    result = run_graph_for_test(question="What is the refund policy?", retrieved_chunks=[PAGE_3_CHUNK])
    assert result.citations[0].page_number == 3
```

- [ ] **Step 2: Run the graph tests to verify failure.**

Run: `pytest tests/rag/test_graph.py tests/rag/test_citations.py -v`

Expected: FAIL because graph and citation services do not exist.

- [ ] **Step 3: Implement the smallest safe graph.**

Define graph state with `workspace_id`, `user_id`, `question`, `route`, `retrieved_chunks`, `answer`, and `citations`. The first version has explicit routes `document_rag` and `summary`; route selection must not grant tool permissions. Retrieval calls `QdrantVectorStore.search` with workspace filter and optional document ID filter. Prompts demand that the answer use only retrieved evidence and output citation chunk IDs. `citations.py` resolves chunk IDs to source name and page number and rejects unknown IDs.

- [ ] **Step 4: Run graph and API streaming tests.**

Run: `pytest tests/rag/test_graph.py tests/rag/test_citations.py tests/api/test_chat.py -v`

Expected: PASS; answers have citations or the exact insufficiency response.

- [ ] **Step 5: Commit cited RAG.**

```bash
git add app/rag app/services/citations.py app/schemas/chat.py app/api/routers/chat.py app/db alembic tests
git commit -m "feat: add cited LangGraph RAG and summaries"
```

## Task 7: Add restricted CSV analysis and local Langfuse tracing

**Files:**
- Create: `app/services/csv_analysis.py`, `app/core/observability.py`, `tests/services/test_csv_analysis.py`, `tests/rag/test_csv_route.py`
- Modify: `app/rag/{graph.py,nodes.py}`, `app/api/routers/chat.py`, `.env.example`, `compose.yaml`

**Interfaces:**
- Produces `CsvOperation(filters: list[Filter], group_by: list[str], aggregations: list[Aggregation])`.
- Produces `run_csv_operation(document_id: UUID, workspace_id: UUID, operation: CsvOperation) -> CsvResult`.
- Produces `trace_graph_run(name: str, metadata: dict[str, str]) -> ContextManager` that excludes raw prompt/document/row values.

- [ ] **Step 1: Write failing calculation and safety tests.**

```python
def test_csv_sum_is_reproducible(sample_sales_csv) -> None:
    result = run_csv_operation(
        sample_sales_csv.document_id,
        sample_sales_csv.workspace_id,
        CsvOperation(filters=[Filter(column="country", operator="eq", value="VN")], group_by=[], aggregations=[Aggregation(column="amount", function="sum")]),
    )
    assert result.values == [{"sum_amount": 1250.0}]


def test_unknown_column_is_rejected(sample_sales_csv) -> None:
    with pytest.raises(InvalidCsvOperation):
        run_csv_operation(sample_sales_csv.document_id, sample_sales_csv.workspace_id, CsvOperation(filters=[Filter(column="DROP TABLE", operator="eq", value="x")], group_by=[], aggregations=[]))
```

- [ ] **Step 2: Run tests to verify failure.**

Run: `pytest tests/services/test_csv_analysis.py tests/rag/test_csv_route.py -v`

Expected: FAIL because CSV operation types and graph route do not exist.

- [ ] **Step 3: Implement validated CSV operations and redacted tracing.**

```python
class Filter(BaseModel):
    column: str
    operator: Literal["eq", "ne", "lt", "lte", "gt", "gte", "contains"]
    value: str | int | float


class Aggregation(BaseModel):
    column: str
    function: Literal["sum", "mean", "count", "min", "max"]


class CsvOperation(BaseModel):
    filters: list[Filter]
    group_by: list[str]
    aggregations: list[Aggregation]


class InvalidCsvOperation(ValueError):
    pass
```

Allow only explicit operators `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, and `contains`, plus aggregate functions `sum`, `mean`, `count`, `min`, and `max`. Validate all column names against the stored CSV schema before data access. Load only the selected workspace's object from MinIO. Return citation data containing source filename, columns, applied filters, and row range/count; returning arbitrary CSV rows is outside the MVP.

Wrap each graph invocation in a Langfuse trace whose metadata contains route, workspace ID hash, model IDs, chunk IDs, latency, and status. Do not send raw question text, document content, or CSV data to Langfuse.

- [ ] **Step 4: Run restricted analytics and trace tests.**

Run: `pytest tests/services/test_csv_analysis.py tests/rag/test_csv_route.py -v`

Expected: PASS; calculation matches fixture, invalid columns fail, and trace metadata excludes protected content.

- [ ] **Step 5: Commit CSV and observability.**

```bash
git add app/services/csv_analysis.py app/core/observability.py app/rag app/api .env.example compose.yaml tests
git commit -m "feat: add safe CSV analytics and local traces"
```

## Task 8: Wire Chainlit UI and verify end-to-end acceptance

**Files:**
- Create: `chainlit_app.py`, `tests/e2e/{conftest.py,test_workspace_rag.py}`, `tests/fixtures/{sample.docx,sample.pdf,scanned.pdf,sales.csv}`, `docs/evaluation/questions.jsonl`, `scripts/seed_eval_data.py`
- Modify: `compose.yaml`, `README.md`

**Interfaces:**
- Chainlit consumes FastAPI's authenticated document and streaming chat APIs only.
- Produces UI actions for login, workspace selection, file upload, document status, question, summary request, and rendered citations.

- [ ] **Step 1: Write failing end-to-end acceptance tests.**

```python
@dataclass
class CsvCitation:
    columns: list[str]


@dataclass
class Answer:
    value: float | None
    citation_sources: list[str]
    citation: CsvCitation


class LiveStack:
    def upload(self, workspace: str, filename: str) -> None: ...
    def ask(self, workspace: str, question: str) -> Answer: ...


@pytest.fixture
def live_stack() -> LiveStack:
    return LiveStack.from_compose_environment()


def test_workspace_a_never_receives_workspace_b_citation(live_stack) -> None:
    live_stack.upload("workspace-a", "a.pdf")
    live_stack.upload("workspace-b", "b.pdf")
    answer = live_stack.ask("workspace-a", "What is the policy in b.pdf?")
    assert "b.pdf" not in answer.citation_sources


def test_csv_calculation_has_file_and_column_evidence(live_stack) -> None:
    live_stack.upload("workspace-a", "sales.csv")
    answer = live_stack.ask("workspace-a", "What is the total amount for VN?")
    assert answer.value == 1250.0
    assert answer.citation.columns == ["country", "amount"]
```

- [ ] **Step 2: Run the end-to-end tests to verify failure.**

Run: `pytest tests/e2e/test_workspace_rag.py -v`

Expected: FAIL until Chainlit, API, worker, Qdrant, MinIO, Ollama, and test fixtures are wired.

- [ ] **Step 3: Implement the narrow UI and evaluation harness.**

`chainlit_app.py` stores the bearer token only in the authenticated user session, sends uploads and questions to FastAPI, streams answer tokens, and renders source name plus page number or CSV column/filter evidence. It must not query databases, MinIO, Qdrant, or Ollama directly. `tests/e2e/conftest.py` implements `LiveStack.from_compose_environment()` with FastAPI requests against the running Compose stack. `questions.jsonl` contains at least 30 Vietnamese/English test cases with question, workspace, expected document, expected page/evidence, route, and expected numeric result when applicable.

- [ ] **Step 4: Run the complete checks.**

Run: `docker compose up -d --build && pytest -q && python scripts/seed_eval_data.py && pytest tests/e2e/test_workspace_rag.py -v`

Expected: all tests pass; supported document fixtures ingest; every answer cites evidence or declares insufficiency; and no cross-workspace citation appears.

- [ ] **Step 5: Commit the UI, evaluation set, and runbook.**

```bash
git add chainlit_app.py tests/e2e tests/fixtures docs/evaluation scripts README.md compose.yaml
git commit -m "feat: add Chainlit UI and MVP acceptance tests"
```

## Plan self-review

- Spec coverage: Tasks 1–8 cover local runtime, workspace roles, all required file types and OCR, Qdrant filtering, RAG/summary, CSV calculations, local Langfuse tracing, citations, security baseline, and end-to-end evaluation.
- No-placeholder scan: checked for `TODO`, `TBD`, “implement later”, and undefined task references; none remain.
- Type consistency: `workspace_id` is a UUID across DB, API, job, vector, graph, and CSV interfaces; document and citation interfaces are defined before their consumers.
