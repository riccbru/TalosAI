from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_reporter_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["reporter"]

    return Agent(
        max_iter=3,
        verbose=True,
        memory=False,
        max_retry_limit=2,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("reporter"),
        role="Technical Documentation Lead",
        goal=(
            "Produce a single parseable JSON report that accurately reflects "
            "all validated findings. Raw JSON only — no markdown, no prose, "
            "no code fences. Output must pass json.loads() with no preprocessing."
        )
    )
