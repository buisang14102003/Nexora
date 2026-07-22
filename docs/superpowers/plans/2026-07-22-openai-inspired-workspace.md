# OpenAI-inspired Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the authenticated RAG workspace a light, spacious, OpenAI-inspired chat experience without changing its data or API behavior.

**Architecture:** Keep the existing React state ownership in `App.tsx`. Adjust the presentational contracts in `Sidebar.tsx` and `ChatView.tsx` so document upload lives with the composer, then replace the workspace-specific CSS with a responsive neutral design system.

**Tech Stack:** React 19, TypeScript, Vite, plain CSS, Vitest.

## Global Constraints

- Update only the authenticated workspace/chat experience.
- Preserve workspace selection, session management, document upload, streaming, citations, and account actions.
- Do not change the authentication screen, API client, backend, or add dependencies.
- Keep visible focus, hover, disabled, error, and responsive states.

---

### Task 1: Restructure workspace presentation

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/components/ChatView.tsx`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: existing `Sidebar` and `ChatView` callback props from `App.tsx`.
- Produces: unchanged callback invocation behavior with semantic classes for the new workspace layout.

- [ ] **Step 1: Confirm the API client regression suite passes before UI-only changes**

Run: `npm test -- --run src/api/client.test.ts`

Expected: all existing API client tests pass.

- [ ] **Step 2: Keep sidebar controls but replace text symbols with accessible UI labels and layout classes**

Implement a `New chat` action, workspace/session section headers, and account menu trigger using existing callbacks. Do not alter `onSelectWorkspace`, `onNewChat`, `onSelectSession`, `onRenameSession`, `onDeleteSession`, or `onLogout` calls.

- [ ] **Step 3: Move document upload beside the composer and retain document context in the empty state**

Render the existing file input inside the composer as an attachment control. Keep its accept string and `onUpload` behavior unchanged. Show uploaded documents as compact status rows only when the conversation is empty.

- [ ] **Step 4: Re-run API client tests**

Run: `npm test -- --run src/api/client.test.ts`

Expected: all tests pass; no API behavior changes.

### Task 2: Apply the light workspace design system

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/components/ChatView.tsx`
- Verify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: the class names emitted by the workspace components.
- Produces: fixed desktop sidebar, centered conversation column, bottom composer, and responsive single-column mobile layout.

- [ ] **Step 1: Replace dark workspace colors with neutral light tokens**

Define neutral canvas, surface, border, muted text, and single dark action color variables. Leave `.auth-page` and `.auth-card` selectors unchanged.

- [ ] **Step 2: Implement the desktop composition**

Style `.app-shell` as a fixed 264px sidebar and flexible content area. Constrain conversation content to approximately 760px. Center the empty state and round the composer into one quiet surface.

- [ ] **Step 3: Implement interactions and accessibility states**

Add hover, `:active`, and `:focus-visible` treatments for buttons, navigation entries, attachment control, textarea, and menu actions. Maintain disabled states without hiding the controls.

- [ ] **Step 4: Implement the mobile collapse**

At widths below 760px, replace the fixed two-column layout with one column, make the sidebar compact and scroll-safe, and keep the composer fully visible without horizontal overflow.

- [ ] **Step 5: Build the frontend**

Run: `npm run build`

Expected: TypeScript and Vite complete with exit status 0.

- [ ] **Step 6: Commit the UI implementation**

Run: `git add frontend/src/components/Sidebar.tsx frontend/src/components/ChatView.tsx frontend/src/styles.css`

Run: `git commit -m "feat: refine workspace chat interface"`
