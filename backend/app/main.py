from fastapi import FastAPI

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.mission import router as mission_router

app = FastAPI(
    version="0.1.0",
    title="TalosAI API",
    redirect_slashes=False,
    docs_url="/talos/docs",
    redoc_url="/talos/redoc",
    description="AI-powered Penetration Testing Agent",
)

@app.get("/talos", tags=["Default"])
async def root():
    return {"message": "Welcome to TalosAI API"}

app.include_router(health_router, prefix="/talos/api/v1/health", tags=["Health"])
app.include_router(auth_router, prefix="/talos/api/v1/auth", tags=["Auth"])
app.include_router(mission_router, prefix="/talos/api/v1/mission", tags=["Mission"])
