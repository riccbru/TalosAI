import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.stats import (
    _utc_now,
    get_db_stats,
    get_ollama_stats,
    get_service_error,
    get_system_stats,
)
from app.db.session import engine, get_db

router = APIRouter()

START_TIME = time.time()


@router.get("")
async def backend_health():
    t0 = time.perf_counter()
    try:
        stats = get_system_stats()
        return {
            "status": "degraded" if stats["warnings"] else "up",
            "timestamp": _utc_now(),
            "uptime_seconds": round(time.time() - START_TIME, 1),
            "response_time_ms": round((time.perf_counter() - t0) * 1000, 3),
            **stats,
        }
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)


@router.get("/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    try:
        stats = await get_db_stats(db, engine)

        return {"timestamp": _utc_now(), **stats}
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)


@router.get("/ollama")
async def ollama_health():
    try:
        stats = await get_ollama_stats()
        return stats
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)
