# Local React RAG UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Chainlit as the primary local UI with a React app that reliably manages workspaces and persisted chat sessions.

**Architecture:** FastAPI owns JWT authentication, workspaces, sessions, messages, and SSE RAG responses. A Vite React app at port 8102 stores only the token in session storage and renders sidebar/workspace/session state from FastAPI.

**Tech Stack:** React, Vite, TypeScript, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Docker Compose.

## Global Constraints

- All UI/API/model services remain local; no hosted assets, CDN, analytics, or remote identity provider.
- Existing `/auth/*`, workspace/document/RAG APIs and Chainlit port 8101 remain compatible.
- Every session/message read or mutation requires current user workspace membership.
- Do not persist JWT in database or browser local storage; use browser session storage only.
- Boss requested direct runtime-first work; use focused migration/API/browser verification, not complete test suite.

---

### Task 1: Persist workspace-scoped chat sessions and messages

**Files:** Modify `app/db/models.py`, `app/schemas/chat.py`, `app/api/routers/chat.py`; create `app/api/routers/sessions.py`, `alembic/versions/<revision>_chat_sessions.py`; modify `app/api/main.py`.

**Interfaces:** Add session CRUD under `/workspaces/{workspace_id}/chat-sessions`; extend `ChatRequest` with optional `session_id`; keep `/workspaces/{workspace_id}/chat` SSE event names unchanged.

- [ ] Add `ChatSession(id, workspace_id, user_id, title, created_at, updated_at)` and `ChatMessage(id, session_id, role, content, citations, created_at)` models; migrate existing answer-only messages only if required by schema constraints.
- [ ] Add list/create/get/rename/delete session routes that verify membership and owner before every session query.
- [ ] Persist user question before running RAG; accumulate streamed answer/citations, persist assistant response once stream completes, and update session timestamp/title.
- [ ] Run Alembic upgrade and focused authenticated API checks for create/list/select/rename/delete and chat-session isolation.
- [ ] Commit with `feat: add persisted workspace chat sessions`.

### Task 2: Add the local React/Vite application and API client

**Files:** Create `frontend/` Vite project files; modify `compose.yaml`; modify FastAPI CORS configuration.

**Interfaces:** Frontend runs port 8102 and calls port 8100 with bearer token. API client exposes auth, workspace, sessions, and SSE chat methods matching Task 1 routes.

- [ ] Scaffold TypeScript Vite with no external UI library; build a small fetch/SSE client that reads token from session storage.
- [ ] Add sign-in and sign-up views; successful sign in stores JWT in session storage and transitions to app shell; logout clears it.
- [ ] Add Compose `frontend` service binding `127.0.0.1:8102:5173` and FastAPI CORS for this exact local origin.
- [ ] Run the frontend container and verify unauthenticated auth view renders at port 8102.
- [ ] Commit with `feat: add local React RAG frontend shell`.

### Task 3: Build sidebar workspace/session flows and cited chat

**Files:** Modify React application components/styles created in Task 2.

**Interfaces:** Workspace creation uses `POST /workspaces`; sessions use Task 1 API; composer uses Task 1's extended SSE chat route.

- [ ] Render left sidebar workspace list, active workspace state, and inline **+ Tạo workspace** form. On successful creation, prepend/select the returned workspace and reload that workspace's sessions.
- [ ] Render session list for active workspace with **Chat mới**, select, rename, and delete controls. Restore persisted messages when a session is selected.
- [ ] Stream cited answer into active transcript; save/reload session state through backend; display sources after assistant messages.
- [ ] Verify two created workspaces remain selectable after reload, sessions remain scoped, and a newly created workspace/session is active immediately.
- [ ] Commit with `feat: add workspace and chat session sidebar`.
