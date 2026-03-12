from app.agents.base import BaseAgent


class Scanner(BaseAgent):
    async def get_commands(self, strategy: str):
        return await self.chat(f"Based on this strategy, give me Nmap commands: {strategy}") # noqa: E501
