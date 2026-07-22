# Workspace Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the full sidebar workspace list with a searchable management screen while supporting rename, pin/unpin, archive, and restore.

**Architecture:** Extend the existing SQLAlchemy/FastAPI workspace resource with pin and archive state, then expose small authenticated mutation endpoints. Keep view selection in `App.tsx`, isolate list transformations in pure frontend helpers, render the manager as a focused React component, and leave chat/document components unchanged.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic, pytest, React 19, TypeScript 5.8, Vite 6, Vitest 3, vanilla CSS.

## Global Constraints

- Keep the existing single-user workspace model and current React application shell.
- Do not add React Router, an icon library, or another frontend dependency.
- The sidebar shows only active pinned workspaces and omits the `Pinned` section when empty.
- Archive retains documents, sessions, messages, memberships, stored originals, and vectors; archived workspaces cannot be used until restored.
- Permanent deletion, organization ownership, sharing, and membership-management UI remain outside scope.
- Preserve existing authentication, chat, upload, session, theme, light/dark, and responsive behavior.
- Use labelled dialogs, inline errors, visible focus, and short transform/opacity transitions; do not add `window.alert` or `window.prompt` interactions.

## File structure

- Create `alembic/versions/006_workspace_management.py`: add and remove workspace pin/archive columns.
- Modify `app/db/models.py`: expose `Workspace.is_pinned` and `Workspace.archived_at`.
- Modify `app/schemas/workspace.py`: validate partial workspace updates and return management metadata.
- Modify `app/services/workspaces.py`: centralize normalized-name conflict checks and state mutations.
- Modify `app/api/routers/workspaces.py`: filtered listing plus update/archive/restore endpoints.
- Modify `app/api/deps.py`: reject archived workspaces from normal workspace-scoped APIs.
- Modify `tests/api/test_workspaces.py`: management endpoint and isolation coverage.
- Modify `tests/api/test_documents.py`: prove archived document endpoints are unavailable.
- Modify `tests/api/test_sessions.py`: prove archived session endpoints are unavailable.
- Modify `tests/api/test_chat.py`: prove archived chat is unavailable.
- Modify `frontend/src/api/client.ts`: management fields and request methods.
- Modify `frontend/src/api/client.test.ts`: request-contract tests.
- Create `frontend/src/workspaces/state.ts`: pure search, pin, and archive fallback selectors.
- Create `frontend/src/workspaces/state.test.ts`: pure-state tests without a new DOM testing dependency.
- Create `frontend/src/components/WorkspaceManager.tsx`: management list, menus, forms, confirmation, and empty states.
- Modify `frontend/src/components/Sidebar.tsx`: manager navigation and pinned-only list.
- Modify `frontend/src/App.tsx`: content-mode and workspace mutation orchestration.
- Modify `frontend/src/styles.css`: manager, sidebar, dialogs, states, responsive, dark theme, and reduced-motion styling.

---

### Task 1: Persist workspace management state

**Files:**
- Create: `alembic/versions/006_workspace_management.py`
- Modify: `app/db/models.py:1-82`
- Test: `tests/api/test_workspaces.py`

**Interfaces:**
- Consumes: existing `Workspace` SQLAlchemy model and Alembic revision `005_chat_sessions`.
- Produces: `Workspace.is_pinned: bool` and `Workspace.archived_at: datetime | None`.

- [ ] **Step 1: Write a failing model persistence test**

Append a test that creates a workspace through the API, loads it from the database, changes both new fields, commits, and reloads it:

```python
from datetime import UTC, datetime
from uuid import UUID

from app.db.models import Workspace
from app.db.session import SessionLocal


def test_workspace_persists_pin_and_archive_state(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    created = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Research"}
    ).json()

    with SessionLocal.begin() as session:
        workspace = session.get(Workspace, UUID(created["id"]))
        assert workspace is not None
        assert workspace.is_pinned is False
        assert workspace.archived_at is None
        workspace.is_pinned = True
        workspace.archived_at = datetime.now(UTC)

    with SessionLocal() as session:
        persisted = session.get(Workspace, UUID(created["id"]))
        assert persisted is not None
        assert persisted.is_pinned is True
        assert persisted.archived_at is not None
```

- [ ] **Step 2: Run the test and verify the missing fields fail**

Run: `pytest tests/api/test_workspaces.py::test_workspace_persists_pin_and_archive_state -v`

Expected: FAIL with `AttributeError` for `is_pinned` or an unmapped-column error.

- [ ] **Step 3: Add the migration and mapped fields**

Create the migration:

```python
"""Add pin and archive state to workspaces."""

from alembic import op
import sqlalchemy as sa


revision = "006_workspace_management"
down_revision = "005_chat_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "archived_at")
    op.drop_column("workspaces", "is_pinned")
```

Add `Boolean` to the SQLAlchemy imports and add these fields to `Workspace`:

```python
is_pinned: Mapped[bool] = mapped_column(
    Boolean, default=False, server_default="false", nullable=False
)
archived_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

- [ ] **Step 4: Apply the migration in the test environment and rerun the test**

Run: `alembic upgrade head && pytest tests/api/test_workspaces.py::test_workspace_persists_pin_and_archive_state -v`

Expected: migration reaches `006_workspace_management`; test PASS.

- [ ] **Step 5: Commit the persistence change**

```bash
git add alembic/versions/006_workspace_management.py app/db/models.py tests/api/test_workspaces.py
git commit -m "feat: persist workspace management state"
```

---

### Task 2: Add workspace management API operations

**Files:**
- Modify: `app/schemas/workspace.py`
- Modify: `app/services/workspaces.py`
- Modify: `app/api/routers/workspaces.py`
- Modify: `tests/api/test_workspaces.py`

**Interfaces:**
- Consumes: `Workspace.is_pinned`, `Workspace.archived_at`, and existing membership-scoped workspace queries.
- Produces: `WorkspaceUpdate`, `GET /workspaces?status=active|archived`, `PATCH /workspaces/{workspace_id}`, `POST /workspaces/{workspace_id}/archive`, and `POST /workspaces/{workspace_id}/restore`.

- [ ] **Step 1: Write failing API tests for list, rename, pin, archive, and restore**

Add focused tests with these assertions:

```python
def test_workspace_management_flow(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    first = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Engineering"}
    ).json()
    second = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Support"}
    ).json()

    renamed = client.patch(
        f"/workspaces/{first['id']}",
        headers=_headers(token),
        json={"name": "Product research", "is_pinned": True},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Product research"
    assert renamed.json()["is_pinned"] is True
    assert renamed.json()["updated_at"]

    active = client.get("/workspaces?status=active", headers=_headers(token))
    assert active.status_code == 200
    assert active.json()[0]["id"] == first["id"]

    archived = client.post(
        f"/workspaces/{first['id']}/archive", headers=_headers(token)
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"]
    assert archived.json()["is_pinned"] is False
    assert [item["id"] for item in client.get(
        "/workspaces?status=active", headers=_headers(token)
    ).json()] == [second["id"]]
    assert [item["id"] for item in client.get(
        "/workspaces?status=archived", headers=_headers(token)
    ).json()] == [first["id"]]

    restored = client.post(
        f"/workspaces/{first['id']}/restore", headers=_headers(token)
    )
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert restored.json()["is_pinned"] is False


def test_archived_workspace_rejects_update(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    workspace = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Archive me"}
    ).json()
    client.post(f"/workspaces/{workspace['id']}/archive", headers=_headers(token))

    response = client.patch(
        f"/workspaces/{workspace['id']}",
        headers=_headers(token),
        json={"name": "Hidden", "is_pinned": True},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Archived workspace cannot be updated"}


def test_other_user_cannot_manage_workspace(client, register_and_login) -> None:
    owner_token = register_and_login("owner@example.test")
    workspace = client.post(
        "/workspaces", headers=_headers(owner_token), json={"name": "Private"}
    ).json()
    other_token = register_and_login("other@example.test")

    assert client.patch(
        f"/workspaces/{workspace['id']}",
        headers=_headers(other_token),
        json={"is_pinned": True},
    ).status_code == 404
    assert client.post(
        f"/workspaces/{workspace['id']}/restore", headers=_headers(other_token)
    ).status_code == 404
```

- [ ] **Step 2: Run the management tests and verify the routes fail**

Run: `pytest tests/api/test_workspaces.py -v`

Expected: new tests FAIL with `405 Method Not Allowed` or response-field validation failures.

- [ ] **Step 3: Define request and response schemas**

Update `app/schemas/workspace.py` with trimmed names, management fields, and partial-update validation:

```python
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Workspace name is required")
        return normalized


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_pinned: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Workspace name is required")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "WorkspaceUpdate":
        if self.name is None and self.is_pinned is None:
            raise ValueError("At least one workspace field is required")
        return self


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_pinned: bool
    archived_at: datetime | None
    updated_at: datetime
```

Keep the existing membership schemas below these definitions.

- [ ] **Step 4: Add minimal service mutations with conflict protection**

Add to `app/services/workspaces.py`:

```python
from datetime import UTC, datetime


class ArchivedWorkspaceUpdateError(Exception):
    pass


def workspace_slug(name: str) -> str:
    return "-".join(name.lower().split())


def update_workspace(
    session: Session,
    workspace: Workspace,
    *,
    name: str | None = None,
    is_pinned: bool | None = None,
) -> Workspace:
    if workspace.archived_at is not None:
        raise ArchivedWorkspaceUpdateError
    if name is not None and name != workspace.name:
        slug = workspace_slug(name)
        conflict = session.scalar(
            select(Workspace).where(
                Workspace.slug == slug,
                Workspace.id != workspace.id,
            )
        )
        if conflict is not None:
            raise WorkspaceNameConflictError
        workspace.name = name
        workspace.slug = slug
    if is_pinned is not None:
        workspace.is_pinned = is_pinned
    session.flush()
    session.refresh(workspace)
    return workspace


def archive_workspace(session: Session, workspace: Workspace) -> Workspace:
    if workspace.archived_at is None:
        workspace.archived_at = datetime.now(UTC)
        workspace.is_pinned = False
        session.flush()
        session.refresh(workspace)
    return workspace


def restore_workspace(session: Session, workspace: Workspace) -> Workspace:
    if workspace.archived_at is not None:
        workspace.archived_at = None
        workspace.is_pinned = False
        session.flush()
        session.refresh(workspace)
    return workspace
```

Change `create_workspace` to call `workspace_slug(name)` so create and rename use the same normalization.

- [ ] **Step 5: Add authenticated router queries and endpoints**

In `app/api/routers/workspaces.py`, import `Query`, `WorkspaceUpdate`, and the service functions. Add a private lookup that includes archived rows while preserving membership isolation:

```python
def workspace_for_user(
    session: Session,
    user_id: UUID,
    workspace_id: UUID,
) -> Workspace:
    workspace = session.scalar(
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(
            Membership.user_id == user_id,
            Workspace.id == workspace_id,
        )
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace
```

Replace listing and add mutations:

```python
@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    status_filter: Annotated[Literal["active", "archived"], Query(alias="status")] = "active",
) -> list[Workspace]:
    query = (
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id)
    )
    if status_filter == "active":
        query = query.where(Workspace.archived_at.is_(None)).order_by(
            Workspace.is_pinned.desc(), Workspace.updated_at.desc(), Workspace.id
        )
    else:
        query = query.where(Workspace.archived_at.is_not(None)).order_by(
            Workspace.archived_at.desc(), Workspace.id
        )
    return list(session.scalars(query))


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update(
    workspace_id: UUID,
    request: WorkspaceUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    workspace = workspace_for_user(session, user.id, workspace_id)
    try:
        return update_workspace(
            session,
            workspace,
            name=request.name,
            is_pinned=request.is_pinned,
        )
    except WorkspaceNameConflictError as exc:
        raise HTTPException(status_code=409, detail="Workspace name already exists") from exc
    except ArchivedWorkspaceUpdateError as exc:
        raise HTTPException(status_code=409, detail="Archived workspace cannot be updated") from exc


@router.post("/{workspace_id}/archive", response_model=WorkspaceResponse)
def archive(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    return archive_workspace(session, workspace_for_user(session, user.id, workspace_id))


@router.post("/{workspace_id}/restore", response_model=WorkspaceResponse)
def restore(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    return restore_workspace(session, workspace_for_user(session, user.id, workspace_id))
```

- [ ] **Step 6: Run backend management tests**

Run: `pytest tests/api/test_workspaces.py tests/services/test_workspaces.py -v`

Expected: all tests PASS, including legacy duplicate-name and membership-isolation tests.

- [ ] **Step 7: Commit the management API**

```bash
git add app/schemas/workspace.py app/services/workspaces.py app/api/routers/workspaces.py tests/api/test_workspaces.py
git commit -m "feat: add workspace management API"
```

---

### Task 3: Block archived workspaces from operational APIs

**Files:**
- Modify: `app/api/deps.py`
- Modify: `tests/api/test_documents.py`
- Modify: `tests/api/test_sessions.py`
- Modify: `tests/api/test_chat.py`

**Interfaces:**
- Consumes: `Workspace.archived_at` and the archive endpoint from Task 2.
- Produces: `require_workspace_membership` returning 404 for archived workspaces across existing document, session, and chat routers.

- [ ] **Step 1: Add failing archived-access tests**

Add one focused test to each API module. The document example is:

```python
def test_archived_workspace_cannot_list_documents(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    workspace_id = _create_workspace(client, token)
    assert client.post(
        f"/workspaces/{workspace_id}/archive", headers=_headers(token)
    ).status_code == 200

    response = client.get(
        f"/workspaces/{workspace_id}/documents", headers=_headers(token)
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found"}
```

Add to `tests/api/test_sessions.py`:

```python
def test_archived_workspace_cannot_access_sessions(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    workspace_id = _workspace(client, token)
    session_id = client.post(
        f"/workspaces/{workspace_id}/chat-sessions", headers=_headers(token)
    ).json()["id"]
    assert client.post(
        f"/workspaces/{workspace_id}/archive", headers=_headers(token)
    ).status_code == 200

    listed = client.get(
        f"/workspaces/{workspace_id}/chat-sessions", headers=_headers(token)
    )
    selected = client.get(
        f"/workspaces/{workspace_id}/chat-sessions/{session_id}",
        headers=_headers(token),
    )

    assert listed.status_code == 404
    assert selected.status_code == 404
```

Add to `tests/api/test_chat.py`:

```python
def test_archived_workspace_cannot_chat(client, register_and_login, monkeypatch) -> None:
    from app.api.routers import chat

    token = register_and_login("owner@example.test")
    workspace_id = _workspace(client, token)
    session_id = client.post(
        f"/workspaces/{workspace_id}/chat-sessions", headers=_headers(token)
    ).json()["id"]
    assert client.post(
        f"/workspaces/{workspace_id}/archive", headers=_headers(token)
    ).status_code == 200
    monkeypatch.setattr(
        chat,
        "run_chat_stream",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("archived chat must stop before retrieval")
        ),
    )

    response = client.post(
        f"/workspaces/{workspace_id}/chat",
        headers=_headers(token),
        json={"question": "Private question", "session_id": session_id},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found"}
```

- [ ] **Step 2: Run archived-access tests and verify current access leaks**

Run: `pytest tests/api/test_documents.py::test_archived_workspace_cannot_list_documents tests/api/test_sessions.py::test_archived_workspace_cannot_access_sessions tests/api/test_chat.py::test_archived_workspace_cannot_chat -v`

Expected: FAIL because the current membership dependency does not inspect workspace archive state.

- [ ] **Step 3: Restrict the shared membership dependency**

Import `Workspace` in `app/api/deps.py` and update the dependency:

```python
def require_workspace_membership(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Membership:
    membership = session.get(
        Membership, {"user_id": user.id, "workspace_id": workspace_id}
    )
    workspace = session.get(Workspace, workspace_id)
    if membership is None or workspace is None or workspace.archived_at is not None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return membership
```

- [ ] **Step 4: Run the operational API suites**

Run: `pytest tests/api/test_documents.py tests/api/test_sessions.py tests/api/test_chat.py tests/api/test_workspaces.py -v`

Expected: all tests PASS; archived access returns 404 and restore remains reachable through its management lookup.

- [ ] **Step 5: Commit archived isolation**

```bash
git add app/api/deps.py tests/api/test_documents.py tests/api/test_sessions.py tests/api/test_chat.py
git commit -m "feat: isolate archived workspaces"
```

---

### Task 4: Add typed frontend management data flow

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`
- Create: `frontend/src/workspaces/state.ts`
- Create: `frontend/src/workspaces/state.test.ts`

**Interfaces:**
- Consumes: Task 2 API contracts.
- Produces: `WorkspaceStatus`, `WorkspaceUpdate`, management client methods, `filterWorkspaces`, `pinnedWorkspaces`, and `nextWorkspaceAfterArchive`.

- [ ] **Step 1: Write failing API-client request tests**

Add tests asserting exact requests:

```typescript
it("lists archived workspaces", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
  const api = createApiClient("token-123", fetcher);

  await api.listWorkspaces("archived");

  expect(fetcher).toHaveBeenCalledWith(
    "http://127.0.0.1:8100/workspaces?status=archived",
    expect.objectContaining({
      headers: expect.objectContaining({ Authorization: "Bearer token-123" }),
    }),
  );
});

it("updates and archives a workspace", async () => {
  const workspace = {
    id: "workspace-1",
    name: "Research",
    slug: "research",
    is_pinned: true,
    archived_at: null,
    updated_at: "2026-07-22T10:00:00Z",
  };
  const fetcher = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(workspace), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const api = createApiClient("token-123", fetcher);

  await api.updateWorkspace("workspace-1", { name: "Research", is_pinned: true });
  await api.archiveWorkspace("workspace-1");

  expect(fetcher).toHaveBeenNthCalledWith(
    1,
    "http://127.0.0.1:8100/workspaces/workspace-1",
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ name: "Research", is_pinned: true }),
    }),
  );
  expect(fetcher).toHaveBeenNthCalledWith(
    2,
    "http://127.0.0.1:8100/workspaces/workspace-1/archive",
    expect.objectContaining({ method: "POST" }),
  );
});
```

- [ ] **Step 2: Write failing pure-state tests**

Create `frontend/src/workspaces/state.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import type { Workspace } from "../api/client";
import { filterWorkspaces, nextWorkspaceAfterArchive, pinnedWorkspaces } from "./state";

const workspaces: Workspace[] = [
  { id: "1", name: "Product Research", slug: "product-research", is_pinned: true, archived_at: null, updated_at: "2026-07-22T12:00:00Z" },
  { id: "2", name: "Support", slug: "support", is_pinned: false, archived_at: null, updated_at: "2026-07-21T12:00:00Z" },
];

describe("workspace state", () => {
  it("filters names without case sensitivity", () => {
    expect(filterWorkspaces(workspaces, "research").map(({ id }) => id)).toEqual(["1"]);
    expect(filterWorkspaces(workspaces, " PRODUCT ").map(({ id }) => id)).toEqual(["1"]);
  });

  it("returns only active pinned workspaces", () => {
    expect(pinnedWorkspaces(workspaces).map(({ id }) => id)).toEqual(["1"]);
  });

  it("selects the first remaining workspace after the active one is archived", () => {
    expect(nextWorkspaceAfterArchive(workspaces, "1", "1")).toBe("2");
    expect(nextWorkspaceAfterArchive([workspaces[0]], "1", "1")).toBeNull();
    expect(nextWorkspaceAfterArchive(workspaces, "2", "1")).toBe("2");
  });
});
```

- [ ] **Step 3: Run frontend tests and verify missing methods/helpers fail**

Run: `cd frontend && npm test`

Expected: FAIL with missing exports or methods.

- [ ] **Step 4: Implement the typed client contract**

Extend the types and client methods in `frontend/src/api/client.ts`:

```typescript
export type WorkspaceStatus = "active" | "archived";

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  is_pinned: boolean;
  archived_at: string | null;
  updated_at: string;
};

export type WorkspaceUpdate = {
  name?: string;
  is_pinned?: boolean;
};
```

Replace and add client methods:

```typescript
listWorkspaces: (status: WorkspaceStatus = "active") =>
  request<Workspace[]>(`/workspaces?status=${status}`),
createWorkspace: (name: string) =>
  request<Workspace>("/workspaces", { method: "POST", body: JSON.stringify({ name }) }),
updateWorkspace: (workspaceId: string, update: WorkspaceUpdate) =>
  request<Workspace>(`/workspaces/${workspaceId}`, {
    method: "PATCH",
    body: JSON.stringify(update),
  }),
archiveWorkspace: (workspaceId: string) =>
  request<Workspace>(`/workspaces/${workspaceId}/archive`, { method: "POST" }),
restoreWorkspace: (workspaceId: string) =>
  request<Workspace>(`/workspaces/${workspaceId}/restore`, { method: "POST" }),
```

- [ ] **Step 5: Implement pure workspace selectors**

Create `frontend/src/workspaces/state.ts`:

```typescript
import type { Workspace } from "../api/client";

export function filterWorkspaces(workspaces: Workspace[], query: string): Workspace[] {
  const normalized = query.trim().toLocaleLowerCase();
  if (!normalized) return workspaces;
  return workspaces.filter(({ name }) => name.toLocaleLowerCase().includes(normalized));
}

export function pinnedWorkspaces(workspaces: Workspace[]): Workspace[] {
  return workspaces.filter(({ archived_at, is_pinned }) => archived_at === null && is_pinned);
}

export function nextWorkspaceAfterArchive(
  activeWorkspaces: Workspace[],
  activeWorkspaceId: string | null,
  archivedWorkspaceId: string,
): string | null {
  if (activeWorkspaceId !== archivedWorkspaceId) return activeWorkspaceId;
  return activeWorkspaces.find(({ id }) => id !== archivedWorkspaceId)?.id ?? null;
}
```

- [ ] **Step 6: Run frontend tests**

Run: `cd frontend && npm test`

Expected: all tests PASS.

- [ ] **Step 7: Commit frontend data contracts**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts frontend/src/workspaces/state.ts frontend/src/workspaces/state.test.ts
git commit -m "feat: add workspace management client state"
```

---

### Task 5: Build the workspace management component

**Files:**
- Create: `frontend/src/components/WorkspaceManager.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `Workspace`, `WorkspaceStatus`, and `filterWorkspaces` from Task 4.
- Produces: `WorkspaceManager` with create/open/update/archive/restore callbacks used by `App.tsx` in Task 6.

- [ ] **Step 1: Define and implement the component contract**

Create `frontend/src/components/WorkspaceManager.tsx` with this public contract:

```typescript
type Props = {
  activeWorkspaces: Workspace[];
  archivedWorkspaces: Workspace[];
  loading: boolean;
  error: string;
  onLoadArchived: () => Promise<void>;
  onCreate: (name: string) => Promise<void>;
  onOpen: (workspaceId: string) => void;
  onUpdate: (workspaceId: string, update: WorkspaceUpdate) => Promise<void>;
  onArchive: (workspaceId: string) => Promise<void>;
  onRestore: (workspaceId: string) => Promise<void>;
};
```

Implement these local states:

```typescript
const [status, setStatus] = useState<WorkspaceStatus>("active");
const [query, setQuery] = useState("");
const [menuId, setMenuId] = useState<string | null>(null);
const [dialog, setDialog] = useState<
  | { type: "create" }
  | { type: "rename"; workspace: Workspace }
  | { type: "archive"; workspace: Workspace }
  | null
>(null);
const [name, setName] = useState("");
const [formError, setFormError] = useState("");
const [pendingId, setPendingId] = useState<string | null>(null);
```

Render semantic elements in this order:

```tsx
<main className="workspace-manager">
  <header className="workspace-manager-header">
    <h1>Workspaces</h1>
    <div className="workspace-manager-tools">
      <label className="workspace-search">
        <span className="sr-only">Search workspaces</span>
        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search workspaces" />
      </label>
      <button className="workspace-new-button" onClick={() => openNameDialog("create")}>New</button>
    </div>
  </header>
  <div className="workspace-tabs" role="tablist" aria-label="Workspace status">
    <button role="tab" aria-selected={status === "active"} onClick={() => setStatus("active")}>Active</button>
    <button role="tab" aria-selected={status === "archived"} onClick={() => void selectArchivedTab()}>Archived</button>
  </div>
  <section className="workspace-table" aria-live="polite">
    <div className="workspace-table-heading"><span>Name</span><span>Modified</span><span>Actions</span></div>
    {visibleWorkspaces.map(renderWorkspaceRow)}
    {visibleWorkspaces.length === 0 && renderEmptyState()}
  </section>
  {dialog && renderDialog()}
</main>
```

Use inline SVG with `aria-hidden="true"` for folder, pin, search, and overflow symbols. The active row menu calls `onOpen`, `onUpdate(id, { is_pinned: !workspace.is_pinned })`, prepares the rename dialog, or prepares the archive confirmation. The archived menu exposes only `Restore`. Close menus on outside pointer and Escape with effect cleanup matching the existing Sidebar pattern.

Name-form submission trims the value, rejects an empty string with `Enter a workspace name.`, awaits the callback, and keeps the dialog open with the thrown API message on failure. Archive confirmation names the workspace and says its documents and chats remain saved but unavailable until restoration.

- [ ] **Step 2: Add the manager visual system**

Add CSS for:

```css
.workspace-manager { grid-column: 2 / -1; min-width: 0; overflow-y: auto; padding: 58px clamp(24px, 6vw, 88px) 72px; background: #fff; }
.workspace-manager-header { display: flex; align-items: center; justify-content: space-between; gap: 28px; max-width: 980px; margin: 0 auto 44px; }
.workspace-manager-header h1 { margin: 0; font-size: clamp(1.8rem, 3vw, 2.35rem); font-weight: 650; letter-spacing: -.045em; }
.workspace-manager-tools { display: flex; align-items: center; gap: 12px; }
.workspace-search input { width: min(34vw, 290px); border: 1px solid #dedee0; border-radius: 18px; padding: 9px 14px; color: #202123; background: #fff; }
.workspace-new-button { border: 0; border-radius: 18px; padding: 9px 17px; color: #fff; background: #202123; font-weight: 650; transition: transform .18s ease, background .18s ease; }
.workspace-new-button:active { transform: scale(.97); }
.workspace-tabs { display: flex; gap: 6px; max-width: 980px; margin: 0 auto 12px; border-bottom: 1px solid #ececee; padding-bottom: 12px; }
.workspace-tabs button { border: 0; border-radius: 16px; padding: 8px 14px; color: #55555a; background: transparent; }
.workspace-tabs button[aria-selected="true"] { color: #202123; background: #ececee; font-weight: 600; }
.workspace-table { max-width: 980px; margin: 0 auto; }
.workspace-table-heading, .workspace-row { display: grid; grid-template-columns: minmax(0, 1fr) 150px 44px; align-items: center; gap: 16px; }
.workspace-table-heading { padding: 12px 14px; color: #6f6f72; font-size: .74rem; font-weight: 600; }
.workspace-row { min-height: 64px; border-bottom: 1px solid #ececee; padding: 8px 8px 8px 14px; border-radius: 12px; }
.workspace-row:hover { background: #f7f7f8; }
.workspace-row-main { display: flex; min-width: 0; align-items: center; gap: 12px; border: 0; color: inherit; background: transparent; text-align: left; }
.workspace-row-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.workspace-modified { color: #6f6f72; font-size: .82rem; font-variant-numeric: tabular-nums; }
.workspace-empty { padding: 72px 24px; color: #6f6f72; text-align: center; }
```

Add matching dark-mode selectors, a `<760px` layout that hides the modified column heading and places row metadata under the name, and `@media (prefers-reduced-motion: reduce)` that removes manager transitions.

- [ ] **Step 3: Type-check the standalone component**

Run: `cd frontend && npm run build`

Expected: build PASS; no missing imports, invalid JSX, or TypeScript errors.

- [ ] **Step 4: Commit the manager component**

```bash
git add frontend/src/components/WorkspaceManager.tsx frontend/src/styles.css
git commit -m "feat: add workspace management screen"
```

---

### Task 6: Integrate manager navigation and workspace mutations

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `WorkspaceManager`, client mutations, `pinnedWorkspaces`, and `nextWorkspaceAfterArchive`.
- Produces: complete create → rename → pin → archive → restore flow and pinned-only sidebar navigation.

- [ ] **Step 1: Simplify the Sidebar contract**

Remove workspace-creation dialog state and imports from `Sidebar.tsx`. Replace its workspace props with:

```typescript
type Props = {
  pinned: Workspace[];
  activeWorkspaceId: string | null;
  managerActive: boolean;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onOpenManager: () => void;
  onSelectWorkspace: (workspaceId: string) => void;
  onNewChat: () => Promise<unknown>;
  onSelectSession: (sessionId: string) => Promise<void>;
  onRenameSession: (session: ChatSession) => Promise<void>;
  onDeleteSession: (session: ChatSession) => Promise<void>;
  onLogout: () => void;
};
```

After `New chat`, render:

```tsx
<button className={managerActive ? "workspace-manager-link active" : "workspace-manager-link"} onClick={onOpenManager}>
  <span className="workspace-manager-link-icon" aria-hidden="true">□</span>
  <span>Workspaces</span>
</button>
{pinned.length > 0 && <div className="sidebar-section workspace-section">
  <div className="sidebar-heading"><span>Pinned</span></div>
  <nav className="workspace-list" aria-label="Pinned workspaces">
    {pinned.map((workspace) => <button key={workspace.id} className={!managerActive && workspace.id === activeWorkspaceId ? "nav-item active" : "nav-item"} onClick={() => onSelectWorkspace(workspace.id)}>{workspace.name}</button>)}
  </nav>
</div>}
```

Use a small inline SVG folder instead of the typographic square in the finished markup.

- [ ] **Step 2: Add App content mode and archived collection**

In `App.tsx`, add:

```typescript
type ContentMode = "workspace" | "manager";

const [contentMode, setContentMode] = useState<ContentMode>("workspace");
const [archivedWorkspaces, setArchivedWorkspaces] = useState<Workspace[]>([]);
const [workspaceLoading, setWorkspaceLoading] = useState(false);
const [workspaceError, setWorkspaceError] = useState("");
```

Import `WorkspaceManager`, `nextWorkspaceAfterArchive`, and `pinnedWorkspaces`. Compute pinned rows with `useMemo`:

```typescript
const pinned = useMemo(() => pinnedWorkspaces(workspaces), [workspaces]);
```

Ensure logout clears both workspace collections and returns content mode to `workspace`.

- [ ] **Step 3: Implement management callbacks**

Add these operations in `App.tsx`:

```typescript
async function loadArchivedWorkspaces() {
  if (!api) return;
  setWorkspaceLoading(true);
  setWorkspaceError("");
  try {
    setArchivedWorkspaces(await api.listWorkspaces("archived"));
  } catch (reason) {
    setWorkspaceError(reason instanceof Error ? reason.message : "We couldn't load archived workspaces.");
  } finally {
    setWorkspaceLoading(false);
  }
}

function openWorkspace(nextWorkspaceId: string) {
  setWorkspaceId(nextWorkspaceId);
  setContentMode("workspace");
}

async function updateWorkspace(workspaceId: string, update: WorkspaceUpdate) {
  if (!api) return;
  const updated = await api.updateWorkspace(workspaceId, update);
  setWorkspaces((current) => current.map((workspace) => workspace.id === updated.id ? updated : workspace));
}

async function archiveWorkspace(targetWorkspaceId: string) {
  if (!api) return;
  const archived = await api.archiveWorkspace(targetWorkspaceId);
  const remaining = workspaces.filter((workspace) => workspace.id !== targetWorkspaceId);
  const nextWorkspaceId = nextWorkspaceAfterArchive(workspaces, workspaceId, targetWorkspaceId);
  setWorkspaces(remaining);
  setArchivedWorkspaces((current) => [archived, ...current.filter((workspace) => workspace.id !== archived.id)]);
  if (targetWorkspaceId === workspaceId) {
    setWorkspaceId(nextWorkspaceId);
    if (!nextWorkspaceId) {
      setSessions([]);
      setSessionId(null);
      setMessages([]);
      setDocuments([]);
    }
  }
  setContentMode("manager");
}

async function restoreWorkspace(workspaceId: string) {
  if (!api) return;
  const restored = await api.restoreWorkspace(workspaceId);
  setArchivedWorkspaces((current) => current.filter((workspace) => workspace.id !== workspaceId));
  setWorkspaces((current) => [restored, ...current]);
}
```

Update `createWorkspace` so success opens the new workspace and keeps the active collection ordered consistently.

- [ ] **Step 4: Render Sidebar and content modes**

Replace the authenticated return with:

```tsx
return <div className={contentMode === "manager" ? "app-shell manager-mode" : "app-shell"}>
  <Sidebar
    pinned={pinned}
    activeWorkspaceId={workspaceId}
    managerActive={contentMode === "manager"}
    sessions={sessions}
    activeSessionId={sessionId}
    onOpenManager={() => setContentMode("manager")}
    onSelectWorkspace={openWorkspace}
    onNewChat={async () => {
      setContentMode("workspace");
      return newChat();
    }}
    onSelectSession={selectSession}
    onRenameSession={renameSession}
    onDeleteSession={deleteSession}
    onLogout={logout}
  />
  {contentMode === "manager" ? <WorkspaceManager
    activeWorkspaces={workspaces}
    archivedWorkspaces={archivedWorkspaces}
    loading={workspaceLoading}
    error={workspaceError}
    onLoadArchived={loadArchivedWorkspaces}
    onCreate={createWorkspace}
    onOpen={openWorkspace}
    onUpdate={updateWorkspace}
    onArchive={archiveWorkspace}
    onRestore={restoreWorkspace}
  /> : <>
    <KnowledgeView workspaceName={activeWorkspace?.name ?? null} documents={documents} onUpload={uploadDocuments} />
    <ChatView workspaceName={activeWorkspace?.name ?? null} documents={documents} messages={messages} isStreaming={streaming} error={error} onUpload={uploadDocuments} onSend={send} />
  </>}
</div>;
```

- [ ] **Step 5: Finish sidebar and manager-mode CSS**

Add:

```css
.workspace-manager-link { display: flex; align-items: center; gap: 10px; width: 100%; margin: 0 0 18px; border: 0; border-radius: 9px; padding: 10px 12px; color: #303033; background: transparent; text-align: left; }
.workspace-manager-link:hover, .workspace-manager-link.active { background: #ececee; }
.workspace-manager-link-icon { display: grid; width: 20px; height: 20px; place-items: center; }
.manager-mode { grid-template-columns: 264px minmax(0, 1fr); }
html[data-theme="dark"] .workspace-manager-link { color: #ececec; }
html[data-theme="dark"] .workspace-manager-link:hover,
html[data-theme="dark"] .workspace-manager-link.active { background: #303030; }
```

Extend the mobile media query so `.workspace-manager` spans the single-column shell and the manager header stacks below 560px.

- [ ] **Step 6: Run frontend tests and build**

Run: `cd frontend && npm test && npm run build`

Expected: all Vitest tests PASS and Vite emits a production bundle without TypeScript errors.

- [ ] **Step 7: Commit the integrated UI**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx frontend/src/styles.css
git commit -m "feat: integrate workspace management flow"
```

---

### Task 7: Verify the complete behavior

**Files:**
- Modify only files required to correct failures directly caused by Tasks 1–6.

**Interfaces:**
- Consumes: complete backend and frontend workspace-management flow.
- Produces: verified migration, tests, production build, and browser interaction evidence.

- [ ] **Step 1: Run migration and backend suite**

Run: `alembic upgrade head && pytest -q`

Expected: database is at `006_workspace_management`; all Python tests PASS.

- [ ] **Step 2: Run frontend suite and production build**

Run: `cd frontend && npm test && npm run build`

Expected: all Vitest tests PASS and the Vite production build succeeds.

- [ ] **Step 3: Start the existing local stack**

Use the repository's documented commands:

```bash
docker compose up -d
uvicorn app.api.main:app --host 127.0.0.1 --port 8100
cd frontend && npm run dev -- --host 127.0.0.1 --port 8102
```

Expected: API responds at `http://127.0.0.1:8100`; frontend loads at `http://127.0.0.1:8102` with no console errors.

- [ ] **Step 4: Verify the end-to-end workspace flow**

In light and dark themes, desktop and a viewport below 760px, verify:

1. Sidebar contains `Workspaces` and no full workspace list.
2. Creating a workspace opens it; pinning adds it under `Pinned`.
3. Search filters the active list case-insensitively.
4. Rename updates both the manager row and pinned sidebar label.
5. Archive confirmation names the workspace; confirming removes it from active and pinned lists.
6. Archived workspace document, session, and chat requests return 404.
7. `Archived` tab lists the item; restore returns it to `Active` unpinned.
8. Empty active, empty archived, and no-search-results states render correctly.
9. Tab, Escape, outside-click, and focus-visible behavior work for menus and dialogs.
10. Browser console remains free of errors.

- [ ] **Step 5: Run diff quality checks**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only intentional workspace-management changes remain.

- [ ] **Step 6: Commit verification fixes if needed**

If verification required corrections, stage only those files and commit:

```bash
git add app frontend tests alembic
git commit -m "fix: complete workspace management verification"
```

If no correction was required, do not create an empty commit.
