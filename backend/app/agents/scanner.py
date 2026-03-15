from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.agents.tools import kali_tool
from app.core.config import settings


def get_scanner_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["scanner"]

    return Agent(
        max_iter=5,
        verbose=True,
        memory=False,
        tools=[kali_tool],
        max_retry_limit=2,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("scanner"),
        role="Reconnaissance Specialist",
        goal=(
            "Execute precise CLI-based discovery and enumeration commands "
            "and return raw tool output verbatim without interpretation, "
            "summarization, or fabrication."
        )
    )
