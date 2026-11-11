"""Shared Gemini call wrapper: client-side throttle + retry/backoff.

Extracted from HybridOrchestratorV2 so every orchestrator (V1 and V2) uses the
exact same resilience: one global throttle to stay under the free-tier rate
limit, and automatic retry on transient errors (429 rate limit, 503/500 server
spikes) with backoff — honoring Gemini's own `retryDelay` on 429 and an
exponential backoff (2,4,8,16,32..60s) on 500/503.

`generate()` returns `(response, latency_seconds)` where latency measures only
the successful network call, so callers can attribute it to usage tracking
exactly as before. Callers remain responsible for parsing and usage recording.
"""
import re
import time
from typing import Callable, Optional

from google import genai

from app.core.config import settings


# Single client + global throttle shared across all orchestrators.
# A per-request timeout is essential: without it a stalled HTTP call hangs the
# worker thread forever — no backoff, no error, the mission just freezes. On
# timeout the call raises and is retried as a transient error (see below).
_REQUEST_TIMEOUT_MS = 60_000  # 60s; manager/scanner responses return in seconds
client = genai.Client(
    http_options=genai.types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS)
)

# Gemini free tier allows ~15 requests/min per model. Stay safely under that with
# a client-side throttle. ~4.5s spacing => <14/min.
_MIN_SECONDS_BETWEEN_CALLS = 4.5
_MAX_RETRIES = 5
_last_call_ts = 0.0


def parse_retry_delay(message: str, fallback: float = 30.0) -> float:
    # Gemini surfaces the suggested wait either as "Please retry in 30.04s"
    # or as a RetryInfo "retryDelay": "30s" field. Honor whichever is present.
    for pattern in (r"retry in ([\d.]+)s", r"retryDelay'?:\s*'?(\d+(?:\.\d+)?)s"):
        match = re.search(pattern, message)
        if match:
            return float(match.group(1)) + 1.0  # small cushion
    return fallback


def generate(
    contents: str,
    *,
    schema=None,
    json_mode: bool = False,
    on_log: Optional[Callable[[str], None]] = None,
    _retry: int = 0,
):
    """Throttled Gemini generate_content with retry/backoff on 429/503/500.

    Returns ``(response, latency_seconds)``. `schema` sets a JSON response schema;
    `json_mode` asks for JSON without a schema; neither => plain text. `on_log`
    (optional) receives a human-readable line on each backoff.
    """
    global _last_call_ts

    wait = _MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_ts)
    if wait > 0:
        time.sleep(wait)

    config = None
    if schema is not None:
        config = genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )
    elif json_mode:
        config = genai.types.GenerateContentConfig(
            response_mime_type="application/json",
        )

    try:
        started = time.monotonic()
        resp = client.models.generate_content(
            contents=contents,
            model=settings.GEMINI_MODEL,
            config=config,
        )
        return resp, time.monotonic() - started
    except Exception as e:
        msg = str(e)
        is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
        is_transient_server = (
            "503" in msg or "UNAVAILABLE" in msg
            or "500" in msg or "INTERNAL" in msg
        )
        # A stalled request hits the client timeout and raises; retry it instead
        # of failing the mission (the previous hang had no timeout at all).
        is_timeout = any(
            s in msg.lower() for s in ("timeout", "timed out", "deadline")
        )
        if (is_rate_limit or is_transient_server or is_timeout) and _retry < _MAX_RETRIES:  # noqa: E501
            if is_rate_limit:
                # 429 carries a precise retryDelay from Google; honor it.
                delay = parse_retry_delay(msg)
                reason = "rate limit (429)"
            else:
                # timeout / 503 / 500: exponential backoff 2,4,8,16,32..60s.
                delay = min(2.0 * (2 ** _retry), 60.0)
                reason = "timeout" if is_timeout else "transient server error (503/500)"  # noqa: E501
            if on_log:
                on_log(
                    f"Gemini {reason}; backing off {delay:.0f}s "
                    f"(retry {_retry + 1}/{_MAX_RETRIES})..."
                )
            time.sleep(delay)
            return generate(
                contents,
                schema=schema,
                json_mode=json_mode,
                on_log=on_log,
                _retry=_retry + 1,
            )
        raise
    finally:
        _last_call_ts = time.monotonic()
