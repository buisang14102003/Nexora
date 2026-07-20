from fastapi import FastAPI

from app.api.routers import auth, documents, workspaces

app = FastAPI(title="Local Workspace RAG")
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(documents.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
