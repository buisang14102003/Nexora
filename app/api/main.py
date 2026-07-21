from fastapi import FastAPI

from app.api.routers import account_page, auth, chat, documents, workspaces

app = FastAPI(title="Local Workspace RAG")
app.include_router(account_page.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
