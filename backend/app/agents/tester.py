from app.agents.base import BaseAgent


class Tester(BaseAgent):
    async def analyze_vulnerabilities(self, scan_data: str):
        return await self.chat(f"Analyze these open ports for CVEs: {scan_data}")
