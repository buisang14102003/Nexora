# Local React RAG UI design

## Goal

Make a local React web application the primary RAG interface, with reliable workspace and chat-session management in a left sidebar. FastAPI remains the API/RAG authority; the existing Chainlit app remains an internal legacy surface at port 8101.

## Runtime

- React + Vite UI: `http://127.0.0.1:8102`.
- FastAPI API/RAG: `http://127.0.0.1:8100`.
- Chainlit legacy UI: `http://127.0.0.1:8101`.
- All services remain local in Docker Compose.

## User experience

### Authentication

The React app provides local Sign in and Sign up views using the existing FastAPI `/auth/login` and `/auth/register` endpoints. The access token is kept in browser session storage, cleared by Logout, and added as a Bearer token to each authenticated API request.

### Workspace sidebar

The left sidebar loads workspaces for the signed-in user from `GET /workspaces`.

- A **+ Tạo workspace** button opens a small inline form in the sidebar.
- Submitting a non-empty name calls `POST /workspaces`.
- On success, the new workspace is inserted into the list and becomes active immediately.
- The active workspace remains selected while browsing its chat sessions. Reloading retrieves the list again and lets the user choose any prior workspace.

### Chat sessions

Sessions belong to one workspace and one user.

- **Chat mới** creates a blank session for the active workspace.
- Sidebar lists that workspace's sessions by most recently updated time.
- Selecting a session restores its messages.
- Users can rename or delete their own sessions.
- Sending a question persists the user message, streams the existing cited RAG response, then persists the completed assistant message and citations.

## API and data model

Add PostgreSQL-backed `ChatSession` and `ChatMessage` records. Every session query is constrained by current user and workspace membership.

- `GET /workspaces/{workspace_id}/chat-sessions`
- `POST /workspaces/{workspace_id}/chat-sessions`
- `GET /workspaces/{workspace_id}/chat-sessions/{session_id}`
- `PATCH /workspaces/{workspace_id}/chat-sessions/{session_id}` for rename
- `DELETE /workspaces/{workspace_id}/chat-sessions/{session_id}`
- Extend the existing chat request with `session_id`; persist messages while keeping the SSE answer/citation contract.

The initial first message can become the default session title, truncated to a safe short length. No chat data is shared across workspaces or users.

## Frontend boundaries

- `frontend/src/api`: token-aware FastAPI client and SSE parsing.
- `frontend/src/auth`: Sign in, Sign up, and session-storage helper.
- `frontend/src/components`: sidebar, workspace form, session list, chat transcript, composer.
- `frontend/src/App.tsx`: route/auth/workspace/session state composition only.

No third-party hosted asset, analytics, CDN, or remote model is added.

## Errors and empty states

- Create-workspace validation is shown beside the sidebar form; duplicate/failure messages use FastAPI's safe detail.
- An empty workspace shows a **Chat mới** prompt.
- A failed stream leaves the user message saved and displays a retry-safe error; it does not fabricate an assistant answer.
- Deleted active session returns the user to a new blank session state.

## Verification

- Register/sign in from port 8102 and confirm authenticated requests include token.
- Create two workspaces; confirm both remain selectable after reload.
- Create, reopen, rename, and delete sessions within a workspace; confirm another user/workspace cannot access them.
- Send RAG question and confirm cited answer streams, then appears after session reload.
- Verify port 8102 UI, port 8100 health, and port 8101 legacy UI start locally.
