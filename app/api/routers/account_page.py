from typing import Annotated

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.db.models import User
from app.services.auth import create_user


router = APIRouter(tags=["account-page"])


def _registration_html(error: str | None = None) -> str:
    error_html = f'<p class="auth-error" role="alert">{error}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Create an account</title>
    <link rel="stylesheet" href="http://127.0.0.1:8101/public/auth.css">
  </head>
  <body class="auth-page">
    <main class="auth-card">
      <div class="auth-mark" aria-hidden="true">R</div>
      <h1 class="auth-title">Create your Local RAG Workspace account</h1>
      <p class="auth-subtitle">Store documents and ask grounded questions in your local workspace.</p>
      {error_html}
      <form class="auth-form" method="post" action="/register">
        <label>Email address <input type="email" name="email" required></label>
        <label>Password <input type="password" name="password" required></label>
        <button type="submit">Create account</button>
      </form>
      <a class="auth-secondary-button" href="http://127.0.0.1:8101">Sign in</a>
    </main>
  </body>
</html>"""


@router.get("/register", response_class=HTMLResponse)
def registration_form() -> HTMLResponse:
    return HTMLResponse(_registration_html())


@router.post("/register", response_class=HTMLResponse)
def register_from_form(
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    session: Session = Depends(get_session),
) -> Response:
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        return HTMLResponse(
            _registration_html("Email and password are required."), status_code=422
        )
    if session.scalar(select(User).where(User.email == normalized_email)):
        return HTMLResponse(
            _registration_html("This email address is already registered."), status_code=409
        )
    create_user(session, normalized_email, password)
    return RedirectResponse("http://127.0.0.1:8101", status_code=303)
