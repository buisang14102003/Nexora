# Chainlit account authentication design

## Goal

Move email/password collection out of the Chainlit conversation. Users register or log in before opening the RAG chat. Once authenticated, the chat only handles workspaces, documents, CSV analysis, summaries, and questions.

## Scope

- Add a local `/register` web form served by the existing FastAPI application.
- Use Chainlit's password authentication screen at port 8101 for `/login`.
- Authenticate both forms against the existing `/auth/register` and `/auth/login` API endpoints.
- Store the FastAPI access token only in the authenticated Chainlit user session.
- Add an Account action in the Chainlit UI that shows the signed-in email and a logout control.
- Remove the chat-based login, registration fallback, and password prompts.

Out of scope: password reset/change, email verification, global user administration, and a separate JavaScript frontend.

## Architecture

```text
Browser -> FastAPI :8100 /register -> POST /auth/register -> PostgreSQL
Browser -> Chainlit :8101 login -> POST /auth/login -> FastAPI :8100
Chainlit authenticated session -> bearer token -> existing FastAPI RAG endpoints
```

FastAPI remains the authority for user credentials and JWTs. Chainlit only validates credentials through `LocalRagApi`, then keeps the returned bearer token and email in its server-side session. No password is stored by Chainlit.

The registration page is intentionally a small server-rendered HTML response. It avoids introducing a second UI framework for a single form and redirects users to Chainlit after successful account creation.

## User flow

1. A new user visits `http://127.0.0.1:8100/register`, enters email and password, and submits.
2. FastAPI forwards the data to the existing registration service. On success it redirects to `http://127.0.0.1:8101`.
3. Chainlit presents its native email/password login screen. Valid credentials create a Chainlit `User` whose metadata includes the FastAPI access token.
4. `on_chat_start` reads that authenticated session, sets the token/email, and shows workspace actions. It never asks for credentials in the conversation.
5. The Account action displays the signed-in email and a logout link/control. Logout ends the Chainlit session and returns to the login screen.

Existing users go directly to port 8101 and log in. `/register` is linked from the login page/help text and remains useful for creating a new local account.

## Components and boundaries

### FastAPI registration page

- Provides `GET /register` and `POST /register`.
- Validates only form presence; the existing `/auth/register` endpoint remains responsible for password handling and duplicate-email errors.
- Renders a clear local error message on failure and a link to Chainlit login for existing users.

### Chainlit authentication adapter

- Implements Chainlit's password-auth callback.
- Calls `LocalRagApi.login(email, password)`.
- Returns no user on invalid credentials; otherwise returns a Chainlit user with email identifier and token metadata.
- Does not call registration and does not expose an API error containing sensitive internals.

### Chainlit account controls

- `on_chat_start` obtains email/token from the authenticated Chainlit user rather than asking via `AskUserMessage`.
- An Account action shows the email, user-facing access state, and logout path.
- Existing workspace, upload, CSV, summary, and RAG handlers continue to use the session token unchanged.

## Error handling

- Registration failure keeps the user on `/register`, preserves no password, and displays a safe error message.
- Invalid login stays on the separate login screen with a generic credential error.
- A missing/expired token prevents access to the RAG handlers and asks the user to log in again; it never prompts for a password in chat.
- A registration/login API outage displays a safe unavailable message without raw response bodies.

## Verification

- Verify `/register` renders, can create a new user, and redirects to Chainlit.
- Verify an existing user can log in through the Chainlit screen and reaches workspace actions without credential messages in chat.
- Verify invalid credentials do not start a chat session.
- Verify the Account action shows the authenticated email and logout ends the session.
- Smoke-check API and Chainlit container health after rebuild.
