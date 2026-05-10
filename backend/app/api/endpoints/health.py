import inspect

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status import (
    get_backend_status,
    get_db_status,
    get_kali_status,
    get_metapsloitable_status,
    get_ollama_status,
    get_service_error,
)
from app.db.session import engine, get_db


router = APIRouter()

services = {
    "kali":             lambda _:  get_kali_status(),
    "ollama":           lambda _:  get_ollama_status(),
    "backend":          lambda _:  get_backend_status(),
    "db":               lambda db: get_db_status(db, engine),
    "metasploitable":   lambda _:  get_metapsloitable_status(),
}


@router.get("/all")
async def get_all_service_status(db: AsyncSession = Depends(get_db)):
    results = {}
    for service_name in services:
        try:
            results[service_name] = await get_service_status(service_name, db)
        except HTTPException as e:
            results[service_name] = {"status": "down", "detail": e.detail}
    return results

@router.get("/{service}")
async def get_service_status(service: str, db: AsyncSession = Depends(get_db)):
    if service not in services:
        raise HTTPException(status_code=404, detail="Service not found")
    try:
        result = services[service](db)
        if inspect.isawaitable(result):
            result = await result
        return result
    except Exception as e:
        return JSONResponse(status_code=503, content=get_service_error(e))
