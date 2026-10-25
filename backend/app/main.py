from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .db import init
from .routers import analysis, auth, history

app = FastAPI(title="SmartAudit AI")
init()
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])

@app.get("/api/health")
def health():
    return {"status": "ok"}

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
