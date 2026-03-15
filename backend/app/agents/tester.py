from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.agents.tools import kali_tool
from app.core.config import settings


def get_tester_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["tester"]

    return Agent(
        max_iter=8,
        verbose=True,
        memory=False,
        tools=[kali_tool],
        max_retry_limit=2,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("tester"),
        role="Exploitation Operator",
        goal=(
            "Prove the existence of vulnerabilities through executed terminal "
            "commands. Return a JSON array of structured evidence objects "
            "for every port and service found in the scanner output. "
            "Never fabricate data. Never use placeholders."
        ),
    )
