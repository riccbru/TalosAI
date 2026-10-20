import litellm
from crewai import LLM

from app.core.config import settings

# CrewAI 1.15 forwards LLM init kwargs down to the provider completion call. The
# Ollama-only `num_ctx` ends up reaching the OpenAI-compatible
# `Completions.create()`, which rejects it ("unexpected keyword argument
# 'num_ctx'") and hangs the synchronous V1 hybrid endpoint. Letting litellm drop
# params a given endpoint does not accept keeps `num_ctx` effective on native
# Ollama calls while never crashing the CrewAI pipeline.
litellm.drop_params = True


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
