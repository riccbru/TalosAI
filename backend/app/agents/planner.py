from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_planner_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["planner"]

    return Agent(
        max_iter=3,
        memory=False,
        verbose=True,
        max_retry_limit=2,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("planner"),
        role="Strategic Security Architect",
        goal=(
            "Produce a target-specific, phased penetration testing plan "
            "with concrete technical objectives for each attack phase. "
            "Output must be a valid JSON object. No prose outside JSON."
        ),
    )
