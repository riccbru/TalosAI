from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.security import decode_access_token


UNPROTECTED_PREFIXES = (
    "/talos/docs",
    "/talos/redoc",
    "/talos/api/auth/",
    "/talos/openapi.json",
)


class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in UNPROTECTED_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid authorization header"}, status_code=401
            )

        payload = decode_access_token(auth_header.removeprefix("Bearer "))
        if not payload:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

        request.state.user = payload.get("user")
        return await call_next(request)
