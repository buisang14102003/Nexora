from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import account_page, auth, chat, documents, sessions, workspaces

app = FastAPI(title="Local Workspace RAG")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8102"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(account_page.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(sessions.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
