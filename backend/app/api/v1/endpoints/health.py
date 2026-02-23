from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_check():
    return {
        "version": "0.1.0",
        "api_version": "v1",
        "status": "healthy",
        "service": "talosai-backend"
    }