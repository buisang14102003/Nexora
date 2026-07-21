# Authentication Navigation Buttons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace raw registration URL text with usable Sign up and Sign in buttons on the local authentication pages.

**Architecture:** A local Chainlit custom JavaScript asset adds one safe anchor after the native login form. The FastAPI registration template adds a semantic secondary Sign in anchor. The existing local stylesheet styles both controls.

**Tech Stack:** Chainlit 2.6.3 custom CSS/JS, FastAPI HTMLResponse, local browser DOM APIs.

## Global Constraints

- All assets remain local; no external CDN, analytics, identity provider, or network request.
- The script must not read, log, store, or submit email/password/token values.
- Preserve the native Chainlit Sign In form and its authentication behavior.
- Preserve FastAPI registration endpoint behavior, errors, and redirects.
- Apply only to Sign in and Sign up pages; use targeted browser smoke checks, not full suite.

---

## File structure

- Create `public/auth-links.js`: idempotently insert the native-login Sign up anchor.
- Modify `.chainlit/config.toml`: load `auth-links.js` after the local CSS.
- Modify `.chainlit/translations/en-US.json`: remove raw registration URL from title while retaining concise login copy.
- Modify `public/auth.css`: add shared secondary button style scoped to auth pages/login root.
- Modify `app/api/routers/account_page.py`: render the Sign in secondary button.

### Task 1: Add local reciprocal authentication buttons

**Files:** Create `public/auth-links.js`; modify `.chainlit/config.toml`, `.chainlit/translations/en-US.json`, `public/auth.css`, `app/api/routers/account_page.py`.

**Interfaces:** Consumes the native Chainlit login form after hydration and existing `/register` route. Produces anchor `#local-rag-sign-up` to `http://127.0.0.1:8100/register` and registration-page Sign in anchor to `http://127.0.0.1:8101`.

- [ ] **Step 1: Create an idempotent local login navigation asset**

```javascript
const registerUrl = "http://127.0.0.1:8100/register";

function addSignUpLink() {
  if (document.getElementById("local-rag-sign-up")) return true;
  const submit = document.querySelector('button[type="submit"]');
  if (!submit) return false;
  const link = document.createElement("a");
  link.id = "local-rag-sign-up";
  link.className = "auth-secondary-button";
  link.href = registerUrl;
  link.textContent = "Sign up";
  submit.insertAdjacentElement("afterend", link);
  return true;
}

const observer = new MutationObserver(() => {
  if (addSignUpLink()) observer.disconnect();
});
observer.observe(document.body, { childList: true, subtree: true });
addSignUpLink();
```

- [ ] **Step 2: Load the local script and remove the raw URL title**

Set `custom_js = "/public/auth-links.js"`. Change the English login title to `Login to Local RAG Workspace` and keep the form labels/actions unchanged.

- [ ] **Step 3: Style the secondary anchors and registration page link**

Add a scoped `.auth-secondary-button` rule with a white background, `#e5e7eb` border, centered label, focus outline, hover background, and full available width. Replace registration page's final paragraph with an anchor using `class="auth-secondary-button"` and label `Sign in`.

- [ ] **Step 4: Targeted acceptance checks**

Run `docker compose up -d --build api chainlit`. At `http://127.0.0.1:8101/login`, verify exactly one clickable Sign up button opens `/register`. At `http://127.0.0.1:8100/register`, verify Sign in returns to port 8101. Verify native Sign In still submits credentials and no browser console errors originate from `auth-links.js`.

- [ ] **Step 5: Commit**

Run `git add public/auth-links.js public/auth.css .chainlit/config.toml .chainlit/translations/en-US.json app/api/routers/account_page.py && git commit -m "feat: add auth navigation buttons"`.
