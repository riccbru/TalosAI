from app.core.ollama import ollama_client


class BaseAgent:
    def __init__(self, role_id: str, config: dict):
        self.role_id = role_id
        self.model = config["model"]
        self.system_prompt = config["system_prompt"]
        self.options = config.get("options", {"temperature": 0.7})

    async def chat(self, prompt: str) -> str:
        response = await ollama_client.generate(
            model=self.model,
            system=self.system_prompt,
            prompt=prompt,
            options=self.options
        )
        return response.get("response", "")
