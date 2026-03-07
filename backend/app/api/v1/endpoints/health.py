import shutil

import psutil
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()

@router.get("/")
async def backend_health():
    try:
        cpu_usage = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        total, used, free = shutil.disk_usage("/")
        body = {
            "status": "up",
            "system": {
                "cpu_load_percent": cpu_usage,
                "memory_usage_percent": memory.percent,
                "disk_free_gb": f"{free / (2 ** 30):.2f}"
            }
        }
        return JSONResponse(status_code=200, content=body)
    except Exception as e:
        body = {
            "status": "down",
            "error": type(e).__name__,
            "message": e.args[-1] if e.args else str(e)
        }
        return JSONResponse(status_code=503, content=body)

@router.get("/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "connected"
        }
    except Exception as e:
        body = {
            "status": "down",
            "error": type(e).__name__,
            "message": e.args[-1] if e.args else str(e)
        }
        return JSONResponse(status_code=503, content=body)
