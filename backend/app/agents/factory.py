import litellm
from crewai import LLM

from app.core.config import settings

# Let litellm drop params a given endpoint does not accept instead of raising.
litellm.drop_params = True


def get_llm_for_agent(agent_key: str) -> LLM:
    config = settings.MODEL_ASSIGNMENT.get(agent_key)

    if not config:
        raise ValueError(f"Agent '{agent_key}' not found in MODEL_ASSIGNMENT")

    # NOTE: `num_ctx` is intentionally NOT passed. CrewAI 1.15 routes `ollama/...`
    # through an OpenAI-compatible client and forwards it straight to
    # `Completions.create()`, which rejects it ("unexpected keyword argument
    # 'num_ctx'") and crashed the local/v1 pipelines. The context window is left
    # to the Ollama model default (set it via the model's Modelfile if needed).
    return LLM(
        timeout=300,
        max_retries=3,
        temperature=config.temperature,
        model=f"ollama/{config.model}",
        base_url=settings.OLLAMA_BASE_URL,
    )
