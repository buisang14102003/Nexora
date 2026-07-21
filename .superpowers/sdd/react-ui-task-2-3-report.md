# React UI tasks 2–3 report

## Status

Implemented the local Vite React UI as the primary interface at `http://127.0.0.1:8102`. Chainlit remains unchanged at port 8101.

## Changes

- Added `frontend/` React + TypeScript + Vite application and Docker image.
- Added local sign-in/sign-up flows. JWT is stored only in browser `sessionStorage`; Logout removes it.
- Added bearer-token API client for workspace/session CRUD and SSE RAG responses.
- Added left sidebar workspace list and inline **+ Tạo workspace** name form. Successful `POST /workspaces` prepends and immediately selects the returned workspace; the normal load path retrieves persisted workspaces after reload.
- Added workspace-scoped **+ Chat mới**, select, rename, delete, and persisted-message restore flows.
- Added streamed answer/citation rendering. Failed streams keep the persisted user message and show an error without fabricating an assistant response.
- Added the Compose `frontend` service on `127.0.0.1:8102:5173` and FastAPI CORS restricted to `http://127.0.0.1:8102`.

## Verification

RED test before implementation:

```text
npm test -- src/api/client.test.ts
FAIL: Cannot find module './client'
```

Final checks:

```text
npm test -- src/api/client.test.ts
1 test passed

npm run build
tsc -b && vite build: passed

docker compose config --quiet
passed

curl OPTIONS /workspaces with Origin: http://127.0.0.1:8102
access-control-allow-origin: http://127.0.0.1:8102
access-control-allow-methods: GET, POST, PATCH, DELETE

docker compose ps frontend api
frontend Up on 127.0.0.1:8102; api Up on 127.0.0.1:8100
```

Browser smoke test at port 8102 passed with no console errors: signed up a local test user, opened the inline workspace form, created **React UI Smoke**, confirmed it became active immediately, and created a **New chat** session visible in the sidebar.

## Concerns

- The full streamed RAG answer was not exercised against a real document/model in this focused smoke test. The frontend SSE parser implements the existing `answer` and `citations` FastAPI contract.
- `npm install` reports two dependency audit advisories. No automatic dependency upgrade was applied because this task pins the runtime stack for reproducible local builds.
