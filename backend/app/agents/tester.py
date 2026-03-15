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
        role="Penetration Tester",
        goal="""Execute technical proof-of-concepts and exploits
        using the kali_terminal to prove vulnerability existence and exploitability."""
    )
