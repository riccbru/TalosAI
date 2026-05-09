from crewai import LLM

from app.core.config import settings


def get_llm_for_agent(agent_key: str) -> LLM:
    config = settings.MODEL_ASSIGNMENT.get(agent_key)

    if not config:
        raise ValueError(f"Agent '{agent_key}' not found in MODEL_ASSIGNMENT")

    return LLM(
        timeout=300,
        max_retries=3,
        num_ctx=config.num_ctx,
        temperature=config.temperature,
        model=f"ollama/{config.model}",
        base_url=settings.OLLAMA_BASE_URL,
    )
