from fastapi import FastAPI

app = FastAPI(title="Local Workspace RAG")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
