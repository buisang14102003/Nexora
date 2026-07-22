# OpenAI-inspired workspace design

## Goal

Refine the React workspace and chat interface into a light, spacious, OpenAI-inspired experience while preserving all existing RAG interactions.

## Scope

- Update only the authenticated workspace/chat experience.
- Keep the existing workspace selection, session management, document upload, streaming, citations, and account actions.
- Do not change the authentication screen, API client, backend, or add dependencies.

## Design

The application uses a neutral light surface with a compact, fixed left sidebar. The sidebar presents a new-chat action, workspaces, session history, and an account control at its base. The main workspace is intentionally sparse: an empty conversation centers a concise prompt and rounded composer; an active conversation uses the same composer at the bottom.

Document upload moves into a compact attachment control in the composer. Documents remain visible as contextual status chips in the empty state. Messages use minimal user and assistant treatments, with citations as clearly separated source references. Controls retain visible focus, hover, disabled, error, and responsive states.

## Verification

- Frontend typecheck and production build succeed.
- Existing frontend API-client tests pass.
- Desktop layout has a fixed sidebar and centered chat column; mobile collapses without horizontal overflow.
