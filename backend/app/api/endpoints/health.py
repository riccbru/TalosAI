from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status import (
    get_db_status,
    get_kali_status,
    get_metapsloitable_status,
    get_ollama_status,
    get_service_error,
    get_system_status,
)
from app.db.session import engine, get_db

router = APIRouter()


@router.get("/system")
async def backend_health():
    try:
        status = get_system_status()
        return status
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)


@router.get("/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    try:
        status = await get_db_status(db, engine)
        return status
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)


@router.get("/ollama")
async def ollama_health():
    try:
        status = await get_ollama_status()
        return status
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)


@router.get("/kali")
async def kali_health():
    try:
        status = await get_kali_status()
        return status
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)


@router.get("/metasploitable")
async def metasploitable_health():
    try:
        status = await get_metapsloitable_status()
        return status
    except Exception as e:
        body = get_service_error(e)
        return JSONResponse(status_code=503, content=body)
