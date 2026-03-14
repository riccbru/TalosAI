from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_scanner_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["scanner"]

    return Agent(
        verbose=True,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("scanner"),
        role="Technical Reconnaissance Specialist",
        goal="Translate strategic plans into precise, executable CLI commands (Nmap, FFUF, Gobuster)", # noqa: E501
        #tools=[nmap_tool]
    )
