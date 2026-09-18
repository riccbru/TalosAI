import os
import sys
import types


# Deterministic settings for the test process. Set before any `app.*` import
# so `app.core.config.settings` (instantiated at import time) picks these up
# instead of relying on a real .env file or a real Postgres/Ollama endpoint.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
os.environ["DEV"] = "false"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["JWT_ALG"] = "HS256"
os.environ["ACCESS_TOKEN_SECRET"] = "test-access-secret"
os.environ["REFRESH_TOKEN_SECRET"] = "test-refresh-secret"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
for _model_var in (
    "GEMINI_MODEL", "PLANNER_MODEL", "SCANNER_MODEL", "TESTER_MODEL",
    "SUMMARIZER_MODEL", "CRITIC_MODEL", "REPORTER_MODEL",
):
    os.environ[_model_var] = ""


def _stub_agent_module(module_name: str, class_name: str) -> None:
    """Stand in for an agents module that fails to import in this environment.

    `app.agents.hybrid_orchestrator_v1`/`_v2` do `from google import genai`
    at module scope, and the `google-genai` package isn't installed here
    (pre-existing, unrelated to auth/sessions — see final report). That
    import failure would otherwise make `app.api.endpoints.missions`
    unimportable, so this replaces just those two modules with a stub
    exposing the same class name before `missions.py` is ever imported.
    Individual tests still monkeypatch the class actually used by
    `missions.py` to control its behavior.
    """
    if module_name in sys.modules:
        return

    stub = types.ModuleType(module_name)

    class _StubOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return {"status": "completed", "stubbed": True}

    setattr(stub, class_name, _StubOrchestrator)
    sys.modules[module_name] = stub


_stub_agent_module("app.agents.hybrid_orchestrator_v1", "HybridOrchestratorV1")
_stub_agent_module("app.agents.hybrid_orchestrator_v2", "HybridOrchestratorV2")

import pytest  # noqa: E402
from fastapi import Depends, FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401 (registers User/UserSession on Base.metadata)
from app.api.deps import auth_scheme, get_current_user  # noqa: E402
from app.api.endpoints.auth import router as auth_router  # noqa: E402
from app.api.endpoints.missions import router as missions_router  # noqa: E402
from app.api.endpoints.sessions import router as sessions_router  # noqa: E402
from app.api.endpoints.status import router as status_router  # noqa: E402
from app.core.middleware import JWTMiddleware  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.users import User, UserRole  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def db_sessionmaker(db_engine):
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
async def db(db_sessionmaker):
    async with db_sessionmaker() as session:
        yield session


@pytest.fixture
def user_factory(db_sessionmaker):
    """Insert a user directly, bypassing /signup, for fast test setup."""

    async def _create(
        email: str = "user@example.com",
        password: str = "Password123!",
        is_active: bool = True,
        role: UserRole = UserRole.user,
    ) -> User:
        async with db_sessionmaker() as session:
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                is_active=is_active,
                role=role,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return _create


@pytest.fixture
def app(db_sessionmaker):
    """App wired the same way as app.main, built from individual routers.

    Not built by importing app.main directly because app.main also pulls in
    the missions router, whose hybrid-orchestrator imports fail in this
    environment due to a pre-existing, unrelated `google.genai` import error
    (see final report) — worked around above via `_stub_agent_module` so the
    real `missions` router/dependencies can still be exercised.
    """
    test_app = FastAPI(redirect_slashes=False)
    test_app.add_middleware(JWTMiddleware)
    test_app.include_router(auth_router, prefix="/talos/api/auth", tags=["Auth"])
    test_app.include_router(
        sessions_router,
        prefix="/talos/api/sessions",
        tags=["Sessions"],
        dependencies=[Depends(auth_scheme)],
    )
    test_app.include_router(
        missions_router,
        prefix="/talos/api/missions",
        tags=["Mission"],
        dependencies=[Depends(auth_scheme), Depends(get_current_user)],
    )
    test_app.include_router(
        status_router,
        prefix="/talos/api/status",
        tags=["Status"],
        dependencies=[Depends(auth_scheme), Depends(get_current_user)],
    )

    async def override_get_db():
        async with db_sessionmaker() as session:
            yield session

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
