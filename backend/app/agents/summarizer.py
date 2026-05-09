from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_summarizer_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["summarizer"]

    return Agent(
        max_iter=3,
        max_retry_limit=2,
        verbose=True,
        memory=False,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("summarizer"),
        role="Output Compression Specialist",
        goal=(
            "Distill verbose raw terminal output into a compact JSON summary "
            "retaining only factual, evidence-backed technical findings. "
            "Never exceed 500 words. Output must be valid JSON only."
        ),
    )
