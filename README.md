# Local RAG Workspace

A local-first, multi-workspace RAG application for asking grounded questions over your documents. Create an account, organize documents into isolated workspaces, and receive answers with source citations—all while keeping models and application data on your machine.

## Highlights

- **Workspace isolation** — accounts, documents, chat sessions, and retrieval are separated by workspace.
- **Document-ready ingestion** — upload CSV, DOCX, PDF, PNG, JPG, or JPEG files up to 25 MB.
- **Rich extraction** — parses document text, OCRs image-based files, and analyzes CSV data.
- **Grounded answers** — a local Ollama chat model answers with citations to the retrieved source material.
- **Privacy-aware observability** — local Langfuse traces exclude prompts, document contents, and CSV values.

## Architecture at a glance

| Layer | Components | Responsibility |
| --- | --- | --- |
| User interfaces | React frontend, Chainlit | Account access, workspaces, uploads, and chat |
| Application | FastAPI API, ingestion worker | Authentication, chat orchestration, document processing |
| Retrieval | Qdrant, Ollama embeddings | Vector indexing and semantic search |
| Storage | Postgres, MinIO | Application data and uploaded files |
| Observability | Langfuse | Local, metadata-only traces |

All services run through Docker Compose. Ollama remains on the host and is reached from containers at `http://host.docker.internal:11434`.

## Prerequisites

- Docker Desktop with Docker Compose
- Ollama available at `http://localhost:11434`
- Python (for environment validation and backend tests)
- Node.js and npm (for frontend tests)

## Quick start

### 1. Configure local secrets

Create your local environment file:

```bash
cp .env.example .env
```

Fill every blank required value in `.env`. The database URL must use the Compose service hostname—not `localhost`—for example:

```dotenv
DATABASE_URL=postgresql+psycopg://rag:<password>@postgres:5432/rag
```

See [`.env.example`](.env.example) for all settings. Keep `.env` local; it contains secrets and is not committed.

### 2. Pull the local models

The defaults are `deepseek-r1:7b` for chat and `qwen3-embedding:0.6b` for embeddings:

```bash
ollama pull deepseek-r1:7b
ollama pull qwen3-embedding:0.6b
```

If you change `CHAT_MODEL` or `EMBEDDING_MODEL` in `.env`, pull those model names instead.

### 3. Validate and start the stack

```bash
python scripts/validate_env.py
docker compose up -d --build
```

### 4. Open the services

| Service | URL | Use |
| --- | --- | --- |
| Registration | http://127.0.0.1:8100/register | Create an account |
| Chainlit workspace | http://127.0.0.1:8101 | Use the Chainlit RAG interface |
| React workspace | http://127.0.0.1:8102 | Use the React frontend |
| Langfuse | http://127.0.0.1:3100 | Inspect local traces |

## Using the workspace

1. Register and sign in.
2. Create a workspace.
3. Upload one or more supported documents.
4. Wait for ingestion to finish, then ask a question in that workspace.
5. Review the citations attached to the answer.

Chat sessions are persisted per workspace. In Chainlit, choose **Account** to see the signed-in email and use the user menu to sign out.

## Configuration

The validation script requires non-empty values for the database, object storage, JWT, Chainlit, and Langfuse secrets before startup. The most commonly adjusted settings are:

| Variable | Purpose | Default |
| --- | --- | --- |
| `CHAT_MODEL` | Ollama model used to generate answers | `deepseek-r1:7b` |
| `EMBEDDING_MODEL` | Ollama model used for vector embeddings | `qwen3-embedding:0.6b` |
| `EMBEDDING_BASE_URL` | Endpoint used by the embedding service | `http://host.docker.internal:11434` |
| `OCR_LANGUAGES` | Tesseract OCR languages | `eng+vie` |

For the complete list, comments, and required secret fields, use [`.env.example`](.env.example).

## How documents are processed

1. Uploaded files are stored in MinIO.
2. The ingestion worker extracts text, runs OCR where needed, and chunks the content.
3. Non-CSV content is embedded and indexed in Qdrant.
4. A question retrieves relevant chunks; Ollama generates a cited answer from that context.

## Development

Run the backend tests:

```bash
python -m pytest
```

Run the frontend tests:

```bash
cd frontend
npm test
```

Validate the Compose configuration:

```bash
docker compose config --quiet
```

## Project layout

```text
app/        FastAPI application, RAG graph, and services
worker/     Background document-ingestion worker
frontend/   React workspace frontend
tests/      Backend and integration tests
scripts/    Setup and environment-validation utilities
compose.yaml Local service stack
```

## UI 
<img width="1915" height="987" alt="image" src="https://github.com/user-attachments/assets/21e1ca70-760e-41d3-8ea9-0e960450370f" />
<img width="1915" height="987" alt="image" src="https://github.com/user-attachments/assets/86869ced-1182-4c77-8615-a6526887b18b" />

