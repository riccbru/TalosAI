from fastapi import FastAPI

from app.api.v1.endpoints.health import router as health_router

app = FastAPI(
    version="0.1.0",
    title="TalosAI API",
    redirect_slashes=False,
    description="AI-powered Penetration Testing Agent"
)

@app.get("/")
async def root():
    return {"message": "Welcome to TalosAI API"}

app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
