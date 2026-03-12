from ollama import AsyncClient

from app.core.config import settings

ollama_client = AsyncClient(
    host=settings.OLLAMA_BASE_URL
    )
