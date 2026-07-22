# Local RAG Workspace

Local-only, multi-workspace retrieval-augmented generation (RAG) application. Upload documents, ask questions against a workspace, and receive answers with citations.

## Features

- Account registration and sign-in
- Isolated workspaces with persisted chat sessions
- Document uploads for CSV, DOCX, PDF, PNG, JPG, and JPEG files (25 MB maximum)
- Text extraction, OCR for image-based documents, and CSV analysis
- Cited RAG answers through a local Ollama chat model
- Local Langfuse tracing that excludes prompts, document contents, and CSV values

## Prerequisites

- Docker Desktop with Docker Compose
- Ollama running on the host at `http://localhost:11434`
- The chat model named by `CHAT_MODEL` in `.env`

## Quick start

1. Create the local configuration file:

   ```bash
   cp .env.example .env
   ```

2. Set every blank required value in `.env`. `DATABASE_URL` must use the Docker hostname, for example:

   ```dotenv
   DATABASE_URL=postgresql+psycopg://rag:<password>@postgres:5432/rag
   ```

3. Pull the configured Ollama chat model. The default is `deepseek-r1:7b`:

   ```bash
   ollama pull deepseek-r1:7b
   ```

4. Validate the configuration and start the stack:

   ```bash
   python scripts/validate_env.py
   docker compose up -d --build
   ```

5. Open the local services:

   | Service | URL |
   | --- | --- |
   | Registration | http://127.0.0.1:8100/register |
   | Chainlit RAG workspace | http://127.0.0.1:8101 |
   | React workspace frontend | http://127.0.0.1:8102 |
   | Langfuse | http://127.0.0.1:3100 |

Register an account, sign in, create a workspace, upload a document, and ask a question. Select **Account** in Chainlit to view the signed-in email; use the Chainlit user menu to sign out.

## Configuration

Start from [`.env.example`](.env.example). The validation command requires non-empty values for the database, storage, JWT, Chainlit, and Langfuse secrets before Docker services start. `CHAT_MODEL` selects the local Ollama chat model; `EMBEDDING_MODEL` and `EMBEDDING_BASE_URL` configure the embedding service.

## Architecture

Docker Compose runs FastAPI, a background ingestion worker, Chainlit, the React frontend, Postgres, MinIO, Qdrant, and the local Langfuse stack. Uploaded files are stored in MinIO; the worker extracts and chunks content, then indexes non-CSV content in Qdrant. The API serves authenticated workspaces, chat sessions, document operations, and cited RAG responses.

## Development

Run the Python tests:

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
