# Workspace management design

## Goal

Replace the full workspace list in the sidebar with a dedicated management screen. The sidebar keeps only pinned workspaces, while the management screen supports creating, finding, opening, renaming, pinning, archiving, and restoring workspaces.

## Scope

- Keep the existing single-user workspace model and current React application shell.
- Add a `Workspaces` navigation action to the sidebar.
- Show only active pinned workspaces in the sidebar.
- Add an in-app workspace management view without introducing a routing dependency or a bookmarkable URL.
- Support workspace search, create, open, rename, pin/unpin, archive, and restore.
- Preserve existing chat, document, authentication, theme, and session behavior.

Permanent deletion, organization-level ownership, sharing, and membership management are outside this change.

## Navigation and layout

The authenticated application has two content modes owned by `App.tsx`:

- **Workspace mode:** the existing knowledge and chat panels.
- **Management mode:** a dedicated workspace management view replacing the knowledge and chat panels.

The sidebar contains:

1. The existing brand and `New chat` action.
2. A `Workspaces` navigation action that opens management mode.
3. A `Pinned` section containing only active workspaces whose `is_pinned` value is true. The section is omitted when empty.
4. The existing `Recent` chat-session list for the active workspace.
5. The existing settings control.

Selecting a pinned workspace makes it active and returns to workspace mode. `New chat` also returns to workspace mode. The selected navigation state clearly distinguishes the workspace manager from an active workspace.

## Workspace management screen

The screen follows the supplied Projects reference while matching the existing neutral Ai-RAG visual system.

### Header

- Left-aligned `Workspaces` heading.
- Search field with the accessible label `Search workspaces`.
- `New` button that opens the existing create-workspace dialog behavior in the new screen context.

### Filters

- `Active` shows all non-archived workspaces.
- `Archived` shows all archived workspaces.
- Search filters the current tab immediately by case-insensitive workspace name.

### List

Each row shows the workspace name, last-modified date, pin state where applicable, and a contextual actions menu.

Active workspace actions:

- `Open`
- `Pin workspace` or `Unpin workspace`
- `Rename`
- `Archive`

Archived workspace actions:

- `Restore`

Clicking the main area of an active row opens the workspace. Archived rows do not open chat, documents, or sessions.

### Empty states

- No active workspaces: explain that workspaces keep documents and chats separate and provide a `New workspace` action.
- No archived workspaces: state that archived workspaces will appear here.
- No search matches: show the current search term and provide a clear-search action.

## Dialogs and feedback

- Create and rename use labelled dialogs with inline validation.
- Rename requires a non-empty trimmed name and reports name conflicts returned by the API.
- Archive uses a confirmation dialog naming the target workspace and explaining that its documents and chats become unavailable until restoration.
- Restore is available directly from the archived row menu.
- An in-flight action disables its own controls to prevent duplicate requests.
- API failures appear near the affected screen or dialog; no new `window.alert` or `window.prompt` interactions are introduced.
- All menus, dialogs, fields, and buttons expose visible keyboard focus and meaningful accessible names.

## Persistence model

Add two fields to `Workspace`:

- `is_pinned`: non-null boolean, default false.
- `archived_at`: nullable timezone-aware timestamp.

Pin state is stored directly on the workspace because this application currently treats workspaces as personal rather than organization-scoped. Archiving always clears `is_pinned`.

The existing `updated_at` value supplies the modified date shown in the management list. Workspace API responses include `is_pinned`, `archived_at`, and `updated_at`.

## API behavior

### Listing

`GET /workspaces?status=active|archived` returns workspaces available to the authenticated user. `status` defaults to `active`, preserving the current application startup behavior.

Ordering is deterministic:

- Active: pinned first, then most recently updated.
- Archived: most recently archived first.

### Updating

`PATCH /workspaces/{workspace_id}` accepts a partial payload containing `name` or `is_pinned` and returns the updated workspace. Empty update payloads are rejected. Archived workspaces cannot be renamed or pinned.

### Archiving and restoring

- `POST /workspaces/{workspace_id}/archive` sets `archived_at`, clears `is_pinned`, and returns the workspace.
- `POST /workspaces/{workspace_id}/restore` clears `archived_at` and returns the workspace unpinned.
- Repeating archive or restore returns the current valid state rather than creating duplicate side effects.

All operations require the same authenticated workspace access checks used by current workspace endpoints.

## Archived-workspace isolation

An archived workspace is retained with all related documents, sessions, messages, memberships, stored originals, and vector data unchanged. It cannot be used for normal application work until restored.

The shared workspace dependency rejects archived workspaces for document listing/upload, session operations, and chat/retrieval requests. Management endpoints use a separate lookup that can access archived records for listing and restoration.

If the currently active workspace is archived, the frontend selects the first remaining active workspace. If none remain, it clears workspace-specific state and stays on the management screen.

## Frontend component boundaries

- `App.tsx` owns content mode, active/archived workspace collections, selection transitions, and API mutations.
- `Sidebar.tsx` renders the management navigation action and pinned active workspaces; it no longer owns the full workspace list or create dialog.
- A focused `WorkspaceManager` component owns search, tab selection, row menus, empty states, and action-dialog presentation.
- The API client adds typed methods for filtered listing, update, archive, and restore.
- Existing knowledge and chat components remain unchanged unless a small prop adjustment is required by the content-mode switch.

No frontend dependency is added. Icons use small inline SVG primitives or the existing typographic treatment consistently; the project does not currently include an icon library.

## Responsive and visual behavior

- Desktop uses an airy list separated by rules instead of a grid of cards.
- The manager occupies the two existing content columns as one scrollable main region.
- Mobile collapses metadata and actions without horizontal scrolling; row menus remain reachable by touch and keyboard.
- Light and dark themes use the current neutral palette, with one restrained active-state treatment.
- Hover, focus, pressed, loading, empty, and error states are present. Motion is limited to short transform and opacity transitions and respects reduced-motion preferences.

## Testing and verification

Backend tests cover:

- Active and archived list filtering and ordering.
- Rename validation and conflict handling.
- Pin and unpin persistence.
- Archive clearing pin state.
- Restore returning the workspace to the active list.
- Archived workspaces being inaccessible to document, session, and chat endpoints.
- One authenticated user being unable to mutate another user's workspace.

Frontend tests cover:

- API client request paths, methods, and payloads.
- Search and Active/Archived filtering behavior.
- Sidebar rendering only active pinned workspaces.
- Active-workspace fallback after archive.

Verification commands:

- Run the targeted Python API/service tests.
- Run the complete Python test suite.
- Run `npm test` in `frontend`.
- Run `npm run build` in `frontend`.
- Visually verify desktop and mobile layouts in light and dark themes, keyboard menu/dialog behavior, and the create → rename → pin → archive → restore flow.

