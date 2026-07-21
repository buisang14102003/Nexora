# Chainlit Account Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move registration and login outside the RAG conversation, then show the signed-in identity through Account controls.

**Architecture:** FastAPI serves a local registration form at `/register` and owns credentials/JWTs. Chainlit 2.6.3 uses its native password callback to authenticate against FastAPI; the JWT remains in authenticated Chainlit-session metadata for existing RAG calls.

**Tech Stack:** FastAPI, server-rendered HTML, Chainlit 2.6.3, httpx, PostgreSQL/JWT.

## Global Constraints

- Keep every service local; add no external identity provider or JavaScript frontend.
- Do not collect or display passwords in a Chainlit message.
- Reuse `POST /auth/register` and `POST /auth/login` as credential authority.
- Preserve the bearer-token interface used by workspace, document, CSV, summary, and RAG calls.
- Boss requested runtime-first verification; run targeted smoke checks, not the full test suite.

---

## File structure

- Modify `app/api/main.py`: mount registration-page router.
- Create `app/api/routers/account_page.py`: serve `GET /register` and `POST /register`.
- Modify `chainlit_app.py`: native password auth, authenticated session initialization, Account action.
- Modify `.chainlit/config.toml` and `README.md`: name/document entry points.

### Task 1: FastAPI registration page

**Files:** Create `app/api/routers/account_page.py`; modify `app/api/main.py`.

**Interfaces:** Consumes `create_user(session, email, password) -> User`, `get_session()`. Produces `GET /register -> HTMLResponse` and `POST /register -> RedirectResponse | HTMLResponse`.

- [ ] **Step 1: Add the router and a focused registration form**

```python
router = APIRouter(tags=["account-page"])

@router.get("/register", response_class=HTMLResponse)
def registration_form() -> HTMLResponse:
    return HTMLResponse(_registration_html())

@router.post("/register", response_class=HTMLResponse)
def register_from_form(
    email: Annotated[str, Form()], password: Annotated[str, Form()],
    session: Session = Depends(get_session),
) -> Response:
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        return HTMLResponse(_registration_html("Email và mật khẩu là bắt buộc."), status_code=422)
    if session.scalar(select(User).where(User.email == normalized_email)):
        return HTMLResponse(_registration_html("Email này đã được đăng ký."), status_code=409)
    create_user(session, normalized_email, password)
    return RedirectResponse("http://127.0.0.1:8101", status_code=303)
```

The form includes email/password inputs, submit button, and link to `http://127.0.0.1:8101` for existing users.

- [ ] **Step 2: Mount the router before the API routers**

```python
from app.api.routers import account_page, auth, chat, documents, workspaces
app.include_router(account_page.router)
app.include_router(auth.router)
```

- [ ] **Step 3: Smoke check**

Run `curl -i http://127.0.0.1:8100/register`; expect HTTP 200 and `Tạo tài khoản` in response.

- [ ] **Step 4: Commit**

Run `git add app/api/main.py app/api/routers/account_page.py && git commit -m "feat: add local registration page"`.

### Task 2: Chainlit native password authentication

**Files:** Modify `chainlit_app.py`.

**Interfaces:** Consumes `LocalRagApi.login(email: str, password: str) -> str`. Produces `authenticate_user(email: str, password: str) -> cl.User | None`, plus authenticated `token`/`email` session values.

- [ ] **Step 1: Replace chat credential prompts with native auth callback**

```python
@cl.password_auth_callback
async def authenticate_user(email: str, password: str) -> cl.User | None:
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        return None
    try:
        token = await _api().login(normalized_email, password)
    except ApiError:
        return None
    return cl.User(identifier=normalized_email, display_name=normalized_email, metadata={"access_token": token})
```

Delete `_authenticate`. `_ask_text` remains only for workspace name and CSV JSON.

- [ ] **Step 2: Initialize RAG session only from authenticated user metadata**

```python
@cl.on_chat_start
async def start() -> None:
    user = cl.user_session.get("user")
    token = user.metadata.get("access_token") if user else None
    if not token:
        await cl.Message(content="Phiên đăng nhập không hợp lệ. Hãy đăng nhập lại.").send()
        return
    cl.user_session.set("token", token)
    cl.user_session.set("email", user.identifier)
    cl.user_session.set("route", "document_rag")
    await cl.Message(content="Đăng nhập thành công. Chọn workspace, sau đó tải tài liệu hoặc gửi câu hỏi.").send()
    await _show_workspace_actions()
```

- [ ] **Step 3: Add Account action**

Append `cl.Action(name="show_account", label="Account", payload={})` to workspace actions and implement:

```python
@cl.action_callback("show_account")
async def show_account(_: cl.Action) -> None:
    await cl.Message(content=f"Tài khoản hiện tại: **{_session('email')}**. Dùng menu người dùng của Chainlit để Đăng xuất.").send()
```

Native Chainlit user menu supplies logout; do not add JWT invalidation.

- [ ] **Step 4: Start-up check**

Run `docker compose up -d --build api chainlit && docker compose ps api chainlit`; expect both `Up` and no callback/import error in Chainlit logs.

- [ ] **Step 5: Commit**

Run `git add chainlit_app.py && git commit -m "feat: use separate Chainlit account login"`.

### Task 3: Documentation and runtime acceptance

**Files:** Modify `.chainlit/config.toml`; modify `README.md`.

**Interfaces:** Consumes FastAPI `/register` and Chainlit login screen. Produces documented local URLs at ports 8100 and 8101.

- [ ] **Step 1: Configure Chainlit identity**

Set `[UI].name = "Local RAG Workspace"` and add login guidance pointing new users to `http://127.0.0.1:8100/register`.

- [ ] **Step 2: Add exact README flow**

Add: `docker compose up -d --build`; new users open port 8100 `/register`; all users log in and use RAG at port 8101; Account shows email and Chainlit user menu logs out.

- [ ] **Step 3: Execute runtime acceptance checks**

Register a fresh disposable email through `/register`; verify 8101 shows a login form before chat; log in and verify workspace actions load without credential chat messages; click Account and verify email; log out and verify the login screen returns.

- [ ] **Step 4: Commit**

Run `git add .chainlit/config.toml README.md && git commit -m "docs: document separate local account flow"`.
