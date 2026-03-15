from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_critic_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["critic"]

    return Agent(
        max_iter=3,
        verbose=True,
        memory=False,
        max_retry_limit=2,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("critic"),
        role="Evidence Auditor",
        goal=(
            "Validate every finding against raw terminal evidence. "
            "Reject any claim not directly supported by tool output. "
            "Output must be a valid JSON audit report."
        )
    )
