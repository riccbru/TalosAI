from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.agents.tools import KaliTerminalTool as kali_tool
from app.core.config import settings


def get_scanner_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["scanner"]

    return Agent(
        verbose=True,
        tools=[kali_tool],
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("scanner"),
        role="Technical Reconnaissance Specialist",
        goal="Translate strategic plans into precise, executable CLI commands (Nmap, FFUF, Gobuster, etc.)" # noqa: E501
    )
