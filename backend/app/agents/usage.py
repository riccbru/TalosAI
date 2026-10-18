"""Universal LLM usage extraction across providers.

Every provider reports token counts under a different shape:

  * Gemini (google-genai): resp.usage_metadata.{prompt_token_count,
    candidates_token_count, total_token_count}
  * Ollama:               resp["prompt_eval_count"], resp["eval_count"]
  * OpenAI / LiteLLM:      resp.usage.{prompt_tokens, completion_tokens,
    total_tokens}
  * Anthropic:            resp.usage.{input_tokens, output_tokens}

`extract_usage()` maps them all to a single (prompt_tokens, completion_tokens,
total_tokens) triple so the rest of the system never has to care which model or
provider produced a call. Everything is best-effort and defensive: an unknown or
malformed response yields zeros rather than raising, because usage telemetry must
never be able to kill a mission.
"""
from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class UsageRecord:
    """One normalized LLM call, attributed to a logical agent."""

    agent: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_seconds: float = 0.0


def _get(obj: Any, *names: str) -> Optional[int]:
    """Read the first present attribute/key across the given names."""
    for name in names:
        value = None
        if isinstance(obj, dict):
            value = obj.get(name)
        else:
            value = getattr(obj, name, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def _finalize(prompt: Optional[int], completion: Optional[int],
              total: Optional[int]) -> Tuple[int, int, int]:
    prompt = prompt or 0
    completion = completion or 0
    if not total:
        total = prompt + completion
    return prompt, completion, total


def _from_gemini(resp: Any) -> Tuple[int, int, int]:
    um = getattr(resp, "usage_metadata", None)
    if um is None and isinstance(resp, dict):
        um = resp.get("usage_metadata") or resp.get("usageMetadata")
    if um is None:
        return 0, 0, 0
    prompt = _get(um, "prompt_token_count", "promptTokenCount")
    completion = _get(um, "candidates_token_count", "candidatesTokenCount")
    total = _get(um, "total_token_count", "totalTokenCount")
    return _finalize(prompt, completion, total)


def _from_ollama(resp: Any) -> Tuple[int, int, int]:
    prompt = _get(resp, "prompt_eval_count")
    completion = _get(resp, "eval_count")
    return _finalize(prompt, completion, None)


def _from_openai_like(resp: Any) -> Tuple[int, int, int]:
    usage = getattr(resp, "usage", None)
    if usage is None and isinstance(resp, dict):
        usage = resp.get("usage")
    if usage is None:
        return 0, 0, 0
    # OpenAI/LiteLLM names first, then Anthropic names.
    prompt = _get(usage, "prompt_tokens", "input_tokens")
    completion = _get(usage, "completion_tokens", "output_tokens")
    total = _get(usage, "total_tokens")
    return _finalize(prompt, completion, total)


def _best_effort(resp: Any) -> Tuple[int, int, int]:
    """Last resort: try the common shapes before giving up with zeros."""
    for extractor in (_from_openai_like, _from_gemini, _from_ollama):
        prompt, completion, total = extractor(resp)
        if total:
            return prompt, completion, total
    return 0, 0, 0


_EXTRACTORS = {
    "gemini": _from_gemini,
    "google": _from_gemini,
    "ollama": _from_ollama,
    "openai": _from_openai_like,
    "anthropic": _from_openai_like,
    "litellm": _from_openai_like,
}


def extract_usage(resp: Any, provider: str) -> Tuple[int, int, int]:
    """Return (prompt_tokens, completion_tokens, total_tokens) for any provider.

    Never raises: an unknown provider or malformed response yields zeros.
    """
    extractor = _EXTRACTORS.get((provider or "").lower(), _best_effort)
    try:
        return extractor(resp)
    except Exception:  # noqa: BLE001 - telemetry must never break a mission
        return 0, 0, 0
