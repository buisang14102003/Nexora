# Local workspace RAG MVP design

## Goal

Build an internal, local-only web application for 10–50 users. Members of a workspace can upload `.csv`, `.docx`, text PDF, and scanned PDF/image documents; ask questions in Vietnamese or English; request cited summaries; and run accurate, controlled calculations over CSV data.

No document content, prompts, embeddings, model inference, or observability trace is sent to an external service.

## Scope

### In scope

- Email/password authentication with hashed passwords.
- Workspaces with `admin` and `member` roles.
- Admin creation and management of workspaces and membership.
- Member document upload and chat within workspaces they belong to.
- Background document ingestion, OCR for scanned PDFs/images, indexing, and retryable job status.
- RAG search and cited answers for PDF and DOCX.
- Cited document summaries.
- Controlled CSV filtering, aggregation, and calculations.
- Self-hosted Langfuse tracing.
- Docker Compose local deployment on a Mac mini M4 with 16 GB RAM and 256 GB SSD.

### Out of scope

- Google Docs, legacy `.doc`, audio/video, handwriting recognition, and external cloud APIs.
- SSO, OAuth, password reset emails, invitations by email, rate limiting, billing, and public internet deployment.
- Cross-workspace document sharing.
- Arbitrary LLM-generated shell, Python, SQL, or database commands.

## Architecture

Docker Compose runs the following local services:

| Service | Responsibility |
| --- | --- |
| Chainlit | Browser chat UI, upload UX, streamed responses. Calls FastAPI only. |
| FastAPI | Authentication, authorization, workspace/document/chat APIs, orchestration entry point. |
| Worker | Background ingestion, OCR, chunking, embeddings, and index updates. |
| PostgreSQL | Users, password hashes, workspaces, memberships, documents, ingestion jobs, chats, messages, and citation records. |
| MinIO | Original uploaded files and generated extraction artifacts. |
| Qdrant | Document chunk vectors plus search payload. |
| Ollama | Local chat model and local embedding model. |
| Langfuse | Local trace UI and trace ingestion. Its own dependencies are isolated from application data stores. |

The browser communicates with Chainlit. Chainlit calls authenticated FastAPI endpoints. FastAPI applies membership checks before any data access, runs the LangGraph workflow for chat, and dispatches slow ingestion work to the worker.

## Authorization and data isolation

Every application record related to a document or conversation carries `workspace_id`. The authenticated user must have a membership row for that workspace before FastAPI returns data, uploads a file, creates a job, or starts a graph run.

Qdrant payload for every chunk includes at least `workspace_id`, `document_id`, `chunk_id`, `source_type`, `source_name`, `page_number`, and source location details. Every vector query includes an exact `workspace_id` filter. The service creates Qdrant payload indexes for fields used for filtering.

Admins manage workspace membership and all workspace documents. Members may upload, view, and query documents in their own workspaces but cannot manage membership.

## Document ingestion

1. FastAPI validates the member, workspace, extension, MIME type, and configured size limit.
2. The original file is stored in MinIO and a `queued` ingestion job is saved in PostgreSQL.
3. The worker selects a parser:
   - DOCX: extract paragraphs and table text.
   - Text PDF: extract page-aware text.
   - Scanned PDF/image: local OCR, retaining page numbers.
   - CSV: parse headers and typed rows; record schema and row count.
4. Text content is normalized and chunked with page/source metadata preserved. CSV is not blindly chunked as prose for numerical work.
5. The worker generates embeddings locally, upserts chunks to Qdrant, and marks the document `ready`.
6. A failed extraction or indexing attempt marks the job `failed` with a safe error reason and can be retried by an authorized user.

The initial ingestion queue is a persistent application job table processed by the worker. Jobs survive application restarts and can later move to a dedicated broker without changing the API contract.

## LangGraph chat workflow

The graph state contains the authenticated user ID, workspace ID, chat history reference, question, selected document IDs if any, route, retrieved evidence, CSV tool result, response, and citations.

1. Validate workspace membership and normalize the request.
2. Classify the intent as `document_rag`, `summary`, or `csv_analysis`.
3. For `document_rag`, embed the question locally, query Qdrant with the workspace filter, and build context from retrieved chunks.
4. For `summary`, retrieve the selected document's chunks, create partial summaries, and reduce them into one cited answer.
5. For `csv_analysis`, validate the requested file and schema, build a restricted structured operation, execute only allowed filter/group/aggregate calculations, and return the result with source columns, filters, and row evidence.
6. Generate the final Vietnamese or English answer through Ollama. The prompt requires use of supplied evidence and requires an explicit insufficiency response when evidence is absent.
7. Validate that every asserted answer has citations. Persist the message and citations, emit a local Langfuse trace, and stream the answer through FastAPI to Chainlit.

The graph does not expose arbitrary code execution. CSV calculations operate on a narrowly defined, validated operation schema rather than untrusted LLM-generated executable code.

## Local model configuration

- Initial chat model: `gemma3:4b` in Ollama.
- Initial embedding model: `qwen3-embedding:0.6b` in Ollama.
- Upgrade path: benchmark `qwen3-embedding:4b` if retrieval quality is insufficient. Benchmark BGE-M3 as a second multilingual embedding candidate.

The model IDs and context settings are configuration values, not hard-coded business logic. Only one primary chat model is loaded for the MVP to stay within the Mac's 16 GB unified memory and 256 GB SSD budget.

## Observability

Langfuse is self-hosted. Each API request and LangGraph node records a trace containing request ID, anonymized user/workspace identifiers, graph route, model ID, retrieval chunk IDs, latency, token or model timing data where available, result status, and safe error details.

Document text, raw prompts, and CSV rows are redacted from traces by default. Diagnostic content may be enabled only through a deliberate workspace-admin setting in a later iteration; it is not part of the MVP UI.

## Failure behavior

- Invalid or unsupported files are rejected before storage with a clear error.
- Parsing, OCR, embedding, or Qdrant errors result in a failed ingestion job and a retry action; existing ready documents remain available.
- An empty or low-confidence retrieval result returns a clear statement that the answer was not found in workspace documents, with no fabricated citation.
- Invalid CSV requests return an explanation of supported filters and aggregations instead of executing code.
- Unavailable Ollama, Qdrant, MinIO, PostgreSQL, worker, or Langfuse results in a retriable service error with request ID. Langfuse outage never exposes document content or blocks the core request after a safe local fallback log.

## Security baseline

- Passwords use a modern password-hash algorithm; plaintext passwords are never stored or logged.
- Secrets live in `.env`, never in source control.
- Services bind to the local machine or private network only for MVP; no service is publicly exposed.
- Upload validation checks extension, MIME type, size, and authorized workspace before storage.
- API authorization is enforced server-side; Chainlit UI state is never trusted for access control.
- Original documents and application databases use persistent local volumes with an operator-managed backup plan.

## Testing and acceptance criteria

### Automated tests

- Unit tests for parsers, chunk metadata, CSV operation validation, citation formatting, and graph route selection.
- API integration tests for login, role checks, workspace isolation, upload lifecycle, retry, and streamed chat response.
- Qdrant integration tests proving every search includes a workspace filter and cannot return another workspace's chunks.
- End-to-end tests covering a text PDF, scanned PDF, DOCX, and CSV.

### Evaluation set

Create a versioned set of at least 30 Vietnamese/English questions sourced from known test documents. It includes document lookup, cross-language lookup, summary, missing-information, and CSV calculation cases. Each case contains expected evidence and expected numerical output where relevant.

### MVP acceptance

- No cross-workspace document or citation appears in authorization and integration tests.
- Every answer contains valid citations or an explicit insufficiency statement.
- Every CSV calculation is compared against its expected result in the evaluation set.
- All four supported document categories complete ingestion or surface a retryable, understandable error.
- Traces appear in self-hosted Langfuse without raw document text by default.

## Delivery sequence

1. Compose runtime and configuration, database schema, authentication, workspaces, and role checks.
2. Upload and persistent ingestion jobs, parsers/OCR, MinIO, embeddings, and Qdrant indexing.
3. LangGraph RAG and summary routes with citations, followed by the Chainlit chat UI.
4. Restricted CSV analytics route.
5. Langfuse integration, evaluation set, and end-to-end acceptance testing.
