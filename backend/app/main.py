from fastapi import FastAPI

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.health import router as health_router
from app.api.endpoints.mission import router as mission_router
from app.core.middleware import JWTMiddleware


app = FastAPI(
    version="0.1.0",
    title="TalosAI API",
    redirect_slashes=False,
    docs_url="/talos/docs",
    redoc_url="/talos/redoc",
    openapi_url="/talos/openapi.json",
    description="AI-powered Penetration Testing Agent",
)


app.add_middleware(JWTMiddleware)


@app.get("/talos/api", tags=["Default"])
async def welcome():
    return {"message": "Welcome to TalosAI API"}


app.include_router(
    tags=["Auth"],
    router=auth_router,
    prefix="/talos/api/auth",
)
app.include_router(
    tags=["System"],
    router=health_router,
    prefix="/talos/api/system",
)
app.include_router(
    tags=["Mission"],
    router=mission_router,
    prefix="/talos/api/missions",
)
