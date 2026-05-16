import inspect
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status import (
    get_backend_status,
    get_database_status,
    get_kali_status,
    get_metapsloitable_status,
    get_ollama_status,
    get_service_error,
)
from app.db.session import engine, get_db


router = APIRouter()

services = {
    "database": lambda db: get_database_status(db, engine),
    "backend": get_backend_status,
    "ollama": get_ollama_status,
    "kali": get_kali_status,
    "metasploitable": get_metapsloitable_status,
}


async def execute_health_check(name: str, db: AsyncSession):
    check = services[name]
    try:
        result = check(db) if inspect.signature(check).parameters else check()

        if inspect.isawaitable(result):
            result = await result
        return result
    except Exception as e:
        raise HTTPException(status_code=503, detail=get_service_error(e))


@router.get("")
@router.get("/{service}")
async def get_service_status(
    service: Optional[str] = None, db: AsyncSession = Depends(get_db)
    ):
    if service is None or service == ":service":
        results = {}
        for s in services:
            try:
                results[s] = await execute_health_check(s, db)
            except HTTPException as e:
                results[s] = e.detail
        return results

    if service not in services:
        valid_options = ", ".join([f"'{s}'" for s in services.keys()])
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found. "
            f"Valid options: {valid_options}",
        )

    return await execute_health_check(service, db)
