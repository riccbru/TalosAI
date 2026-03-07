from api.v1.endpoints.health import router as health_router
from fastapi import FastAPI

app = FastAPI(
    version="0.1.0",
    title="TalosAI API",
    description="AI-powered Penetration Testing Agent"
)
app.include_router(health_router, prefix="/api/v1/health")


@app.get("/")
async def root():
    return {"message": "Welcome to TalosAI API"}

