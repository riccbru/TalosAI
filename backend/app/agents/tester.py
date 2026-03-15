from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.agents.tools import kali_tool
from app.core.config import settings


def get_tester_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["tester"]

    return Agent(
        verbose=True,
        tools=[kali_tool],
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("tester"),
        role="Exploitation Analyst",
        goal="Identify vulnerabilities and CVEs based on reconnaissance data"
    )
