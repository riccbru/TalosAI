from typing import List

import ollama

from app.core.config import settings


class OllamaProvider:
    @staticmethod
    def get_installed_models() -> List[str]:
        try:
            client = ollama.Client(host=settings.OLLAMA_BASE_URL)
            response = client.list()
            return [model["name"] for model in response.get("models", [])]
        except Exception:
            return ["llama3", "mistral"]


AVAILABLE_MODELS = OllamaProvider.get_installed_models()
