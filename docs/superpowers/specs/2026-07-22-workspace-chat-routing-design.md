# Workspace and chat routing design

## Goal

Make Chat and Workspace management separate browser routes so navigation, refresh, and Back/Forward behavior match the visible screen.

## Root cause

The current application switches between Chat and Workspace management with React-only `contentMode` state while the URL remains `/`. A workspace row click can change the rendered content, but browser history and refresh have no representation of that transition. The visible screen and browser location can therefore diverge.

## Route contract

- `/chat` renders the existing Knowledge and Chat panels.
- `/workspaces` renders the existing Workspace management screen.
- `/` is normalized to `/chat` with `history.replaceState`, so it does not add a history entry.
- Any unsupported frontend pathname is normalized to `/chat` with `history.replaceState`.

Authentication remains outside the route distinction. An unauthenticated user sees the existing authentication view at either supported path. After authentication, the application renders the screen represented by the current path.

## Navigation behavior

The application uses a small internal route utility built on the browser History API; no routing dependency is added.

- The route is initialized from `window.location.pathname`.
- `navigate(path)` calls `history.pushState` only when the target differs from the current route, then updates React route state.
- A `popstate` listener updates React route state for browser Back and Forward actions and is removed during cleanup.
- `contentMode` is removed. The normalized route becomes the only source of truth for deciding which main screen to render and which sidebar navigation item is active.

Transitions are explicit:

- Sidebar `Workspaces` → `/workspaces`.
- Selecting a pinned workspace → set active workspace, then `/chat`.
- Selecting or opening a workspace from the manager → set active workspace, then `/chat`.
- `New chat` → `/chat`, then create the session with the existing active workspace.
- Creating a workspace → select the new workspace, then `/chat`.
- Archive, restore, rename, pin/unpin, search, and Active/Archived filters stay on `/workspaces`.
- Logging out keeps the current supported route; authentication replaces the protected content until the next successful login.

## Component boundaries

- Create `frontend/src/routing/app-route.ts` for route types, normalization, and the History API hook.
- `App.tsx` consumes the hook, performs navigation alongside existing workspace/session state updates, and renders by route.
- `Sidebar.tsx` continues to receive callbacks and a boolean active state; it does not access `window` or own routing logic.
- `WorkspaceManager.tsx`, Knowledge, Chat, API clients, and backend endpoints remain unchanged.

## Error and edge behavior

- Calling `navigate` for the route already shown is a no-op and does not create duplicate history entries.
- Direct refresh at `/chat` or `/workspaces` preserves the intended screen after the frontend loads.
- Back/Forward changes only the screen route; existing workspace/session state remains intact during the SPA lifetime.
- If no active workspace exists, `/chat` keeps the current disabled/empty Chat behavior rather than redirecting to Workspace management.
- Route normalization never throws when rendered outside a browser during server-rendered tests; `/chat` is the fallback.

## Testing and verification

Automated tests cover:

- `/`, unknown paths, `/chat`, and `/workspaces` normalization.
- Same-route navigation not adding a history entry.
- Route changes updating the History API and React state.
- `popstate` updating the rendered route.
- Existing Sidebar and WorkspaceManager structural tests continue to pass.
- Frontend production build succeeds.

Browser verification covers:

1. Load `/chat` and open `/workspaces` from the sidebar.
2. Select an active workspace and confirm the URL and content both become `/chat`.
3. Use browser Back and Forward and confirm the visible screen follows the URL.
4. Refresh `/chat` and `/workspaces` and confirm each screen persists.
5. Confirm there are no console errors.

## Non-goals

- No React Router dependency.
- No workspace or session IDs in the URL.
- No deep link to an individual chat session.
- No backend route or database change.
- No visual redesign or unrelated refactor.
