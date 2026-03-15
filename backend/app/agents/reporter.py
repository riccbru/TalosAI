from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_reporter_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["reporter"]

    return Agent(
        verbose=True,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("reporter"),
        role="Technical Documentation Lead",
        goal="Synthesize complex data into executive summaries and structured JSON reports" # noqa: E501
    )
