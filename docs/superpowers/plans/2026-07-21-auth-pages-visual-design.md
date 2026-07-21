# Local RAG Auth Pages Visual Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the local Sign in and Sign up pages a consistent, minimal visual design without changing authentication behavior.

**Architecture:** A single local stylesheet in Chainlit's `public` folder styles the native Chainlit login and is linked by FastAPI's server-rendered registration page. Existing FastAPI registration and Chainlit login handlers remain unchanged.

**Tech Stack:** Chainlit 2.6.3 custom CSS, FastAPI HTMLResponse, local CSS, Docker Compose.

## Global Constraints

- Keep every service local; use no external image, font, CDN, identity provider, or JavaScript frontend.
- Do not alter `/auth/register`, `/auth/login`, JWT handling, or Chainlit authentication callback behavior.
- Preserve native input labels, password masking, focus state, and accessible registration error messages.
- Apply the design only to Sign in and Sign up, not the RAG chat UI.
- Boss requested runtime-first verification; use browser smoke checks rather than full test suite.

---

## File structure

- Create `public/auth.css`: shared local visual tokens and authentication-page styles.
- Modify `.chainlit/config.toml`: set `custom_css = "/public/auth.css"` so Chainlit login loads the stylesheet.
- Modify `app/api/routers/account_page.py`: link the same local stylesheet and add semantic card/identity markup only.

### Task 1: Build the shared local authentication visual system

**Files:**

- Create: `public/auth.css`
- Modify: `.chainlit/config.toml`
- Modify: `app/api/routers/account_page.py`

**Interfaces:**

- Consumes: Chainlit's static path `/public/auth.css` and `_registration_html(error: str | None = None) -> str`.
- Produces: the native sign-in appearance at port 8101 and matching registration appearance at port 8100; registration GET/POST status and redirects remain unchanged.

- [ ] **Step 1: Create a local stylesheet with fixed tokens and responsive card layout**

Create `public/auth.css` with system font stack, `#f7f7f8` page background, a white centered card, `#202123` text, `#6b7280` muted text, `#10a37f` primary controls, visible focus outlines, and a mobile media query. Scope FastAPI styles with `.auth-page`, `.auth-card`, `.auth-mark`, `.auth-title`, `.auth-subtitle`, `.auth-error`, `.auth-link`; use Chainlit login selectors only to center its native form and apply the same card/tokens without hiding controls.

- [ ] **Step 2: Load it in Chainlit**

Replace the commented configuration line with:

```toml
custom_css = "/public/auth.css"
```

Do not add custom JavaScript.

- [ ] **Step 3: Add matching semantic markup to registration page**

Update `_registration_html` so its `<head>` contains:

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="http://127.0.0.1:8101/public/auth.css">
```

and its body follows this structure while preserving the current form field names, method, action, required attributes, and error status:

```html
<body class="auth-page">
  <main class="auth-card">
    <div class="auth-mark" aria-hidden="true">R</div>
    <h1 class="auth-title">Create your Local RAG Workspace account</h1>
    <p class="auth-subtitle">Keep your documents and answers inside your local workspace.</p>
    <p class="auth-error" role="alert">…only when an error exists…</p>
    <form class="auth-form" method="post" action="/register">…</form>
    <p class="auth-link">Already have an account? <a href="http://127.0.0.1:8101">Sign in</a></p>
  </main>
</body>
```

- [ ] **Step 4: Run targeted visual and behavior checks**

Run `docker compose up -d --build api chainlit`. Open `http://127.0.0.1:8101/login` and `http://127.0.0.1:8100/register`; expect an off-white centered-card layout, native login controls, and reciprocal sign-up/sign-in guidance. Submit an existing email to `/register`; expect HTTP 409 and a visible card error. Narrow the browser viewport; expect card remains readable with no horizontal scrolling.

- [ ] **Step 5: Commit**

Run `git add public/auth.css .chainlit/config.toml app/api/routers/account_page.py && git commit -m "feat: style local authentication pages"`.
