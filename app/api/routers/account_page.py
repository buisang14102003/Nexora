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
<html lang="vi">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Tạo tài khoản</title>
    <link rel="stylesheet" href="http://127.0.0.1:8101/public/auth.css">
  </head>
  <body class="auth-page">
    <main class="auth-card">
      <div class="auth-mark" aria-hidden="true">R</div>
      <h1 class="auth-title">Tạo tài khoản Local RAG Workspace</h1>
      <p class="auth-subtitle">Lưu trữ và hỏi đáp tài liệu ngay trong không gian làm việc nội bộ.</p>
      {error_html}
      <form class="auth-form" method="post" action="/register">
        <label>Địa chỉ email <input type="email" name="email" required></label>
        <label>Mật khẩu <input type="password" name="password" required></label>
        <button type="submit">Tạo tài khoản</button>
      </form>
      <a class="auth-secondary-button" href="http://127.0.0.1:8101">Đăng nhập</a>
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
            _registration_html("Email và mật khẩu là bắt buộc."), status_code=422
        )
    if session.scalar(select(User).where(User.email == normalized_email)):
        return HTMLResponse(
            _registration_html("Email này đã được đăng ký."), status_code=409
        )
    create_user(session, normalized_email, password)
    return RedirectResponse("http://127.0.0.1:8101", status_code=303)
