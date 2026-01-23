"""FastAPI main application entry point"""

from fastapi import FastAPI
from datetime import datetime
from app import __version__

app = FastAPI(title="Sentinel", version=__version__)

@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": "Welcome to Sentinel", "timestamp": datetime.now().isoformat()}

@app.get("/health")
async def health_check() -> dict[str, str | datetime]:
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": __version__
    }
