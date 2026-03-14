from crewai import Agent

from app.agents.factory import get_llm_for_agent
from app.core.config import settings


def get_critic_agent() -> Agent:
    config = settings.MODEL_ASSIGNMENT["critic"]

    return Agent(
        verbose=True,
        allow_delegation=False,
        backstory=config.system_prompt,
        llm=get_llm_for_agent("critic"),
        role="Safety & Syntax Validator",
        goal="Review all proposed CLI commands for accuracy, safety, and logical consistency" # noqa: E501
    )
