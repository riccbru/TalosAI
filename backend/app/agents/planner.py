from app.agents.base import BaseAgent


class Planner(BaseAgent):
    async def create_plan(self, target: str):
        return await self.chat(f"Create a step-by-step pentest plan for {target}")
