"""Centralized, client-safe error handling.

Security note (CodeQL `py/stack-trace-exposure`): raw exception text, stack
traces and upstream-provider messages must NEVER reach an HTTP client. Doing so
leaks internal implementation details (file paths, library versions, SQL, host
names) that help an attacker. This module is the single boundary where that
rule is enforced:

- the full exception / failure detail is logged server-side (with traceback),
- the client only ever receives a stable ``error_code`` plus a fixed, generic
  message looked up from ``CLIENT_MESSAGES`` — never anything derived from the
  exception instance.

Every endpoint should build its error responses through the helpers here
instead of serialising exceptions or orchestrator failure dicts directly.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import status
from fastapi.responses import JSONResponse


logger = logging.getLogger("talos.errors")


class ErrorCode:
    """Stable, client-facing error codes (safe to expose and to switch on)."""

    PROVIDER_UNREACHABLE = "PROVIDER_UNREACHABLE"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    ORCHESTRATION_FAILED = "ORCHESTRATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Fixed, generic messages. These are constants — never interpolate exception
# text, user input or upstream payloads into them.
CLIENT_MESSAGES = {
    ErrorCode.PROVIDER_UNREACHABLE: (
        "Could not reach the AI model provider. Please try again shortly."
    ),
    ErrorCode.UPSTREAM_ERROR: (
        "The AI model provider returned an error. Please try again shortly."
    ),
    ErrorCode.CONFIG_ERROR: "Invalid agent or task configuration.",
    ErrorCode.ORCHESTRATION_FAILED: "The mission could not be completed.",
    ErrorCode.INTERNAL_ERROR: "An unexpected internal error occurred.",
}

# Which error codes map to which HTTP status.
_STATUS_BY_CODE = {
    ErrorCode.PROVIDER_UNREACHABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.UPSTREAM_ERROR: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.CONFIG_ERROR: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ORCHESTRATION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def classify_exception(e: BaseException) -> str:
    """Map an exception to a stable, client-safe error code."""
    name = type(e).__name__
    if "APIConnectionError" in name or "ConnectionError" in name:
        return ErrorCode.PROVIDER_UNREACHABLE
    if "APIError" in name or "APIStatusError" in name:
        return ErrorCode.UPSTREAM_ERROR
    if "ValidationError" in name:
        return ErrorCode.CONFIG_ERROR
    return ErrorCode.ORCHESTRATION_FAILED


def _body(error_code: str, target: Optional[str]) -> dict:
    """Build a sanitized response body containing no exception-derived data."""
    body: dict[str, Any] = {
        "status": "failed",
        "error_code": error_code,
        "message": CLIENT_MESSAGES.get(
            error_code, CLIENT_MESSAGES[ErrorCode.INTERNAL_ERROR]
        ),
    }
    if target is not None:
        body["target"] = target
    return body


def error_response(
    error_code: str,
    target: Optional[str] = None,
    status_code: Optional[int] = None,
) -> JSONResponse:
    """A sanitized ``JSONResponse`` built only from the error code."""
    resolved = status_code or _STATUS_BY_CODE.get(
        error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    return JSONResponse(status_code=resolved, content=_body(error_code, target))


def handle_exception(
    e: BaseException,
    context: str,
    target: Optional[str] = None,
) -> JSONResponse:
    """Log an exception server-side and return a sanitized ``JSONResponse``.

    The full exception and traceback go to the logs only; the client receives a
    stable code and a generic message.
    """
    error_code = classify_exception(e)
    logger.exception("%s failed [%s]", context, error_code)
    return error_response(error_code, target=target)


def handle_failure_result(
    result: dict,
    context: str,
    target: Optional[str] = None,
    error_code: str = ErrorCode.ORCHESTRATION_FAILED,
    status_code: Optional[int] = None,
) -> JSONResponse:
    """Turn an orchestrator failure dict into a sanitized ``JSONResponse``.

    Orchestrator results may embed raw exception text (``detail``, ``message``,
    ...). We log the whole result server-side and hand the client only the code
    and a generic message, so nothing sensitive crosses the boundary.
    """
    logger.error("%s reported a failure result: %r", context, result)
    return error_response(error_code, target=target, status_code=status_code)


def log_detail(context: str, detail: Any) -> None:
    """Record internal failure detail server-side (never returned to clients)."""
    logger.error("%s: %r", context, detail)
