from app.agents.base import BaseAgent


class Reporter(BaseAgent):
    async def compile_report(self, mission_data: str):
        return await self.chat(f"Summarize this data into minified JSON: {mission_data}")
