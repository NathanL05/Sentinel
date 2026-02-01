"""FastAPI main application entry point"""

from datetime import datetime, timezone

from fastapi import FastAPI

from app import __version__
from app.routers.metrics import router

app = FastAPI(title="Sentinel", version=__version__)

app.include_router(router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": "Welcome to Sentinel", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health")
async def health_check() -> dict[str, str | datetime]:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
    }
