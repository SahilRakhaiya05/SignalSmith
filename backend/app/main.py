from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import reload_settings
from app.logging_config import setup_logging
from app.middleware import RequestContextMiddleware

setup_logging()
reload_settings()
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(
    title="SignalSmith AI",
    description="Cut telemetry cost without cutting incident coverage.",
    version="3.0.0",
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/api")
async def api_root():
    return {
        "name": "SignalSmith AI",
        "version": "3.0.0",
        "tagline": "Cut telemetry cost without cutting incident coverage.",
        "docs": "/docs",
        "health": "/api/health",
        "integrations": "/api/integrations/status",
        "ui": "/",
    }


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_ui():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        if path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = FRONTEND_DIST / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
else:

    @app.get("/")
    async def root_fallback():
        return {
            "name": "SignalSmith AI",
            "version": "3.0.0",
            "message": "Frontend not built. Run: cd frontend && npm run build",
            "docs": "/docs",
            "health": "/api/health",
        }