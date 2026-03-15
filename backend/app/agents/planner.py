from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_planner_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["planner"]

    return Agent(
        memory=True,
        verbose=True,
        allow_delegation=True,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("planner"),
        role="Strategic Security Architect",
        goal="Develop a non-linear, stealthy pentest strategy focusing on targets requested" # noqa: E501
    )
