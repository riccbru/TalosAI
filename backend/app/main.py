from fastapi import Depends, FastAPI

from app.api.deps import auth_scheme
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.missions import router as missions_router
from app.api.endpoints.sessions import router as sessions_router
from app.api.endpoints.status import router as status_router
from app.api.endpoints.users import router as users_router
from app.core.config import settings
from app.core.middleware import JWTMiddleware


env_dev = settings.DEV is True


app = FastAPI(
    version="0.1.0",
    title="TalosAI API",
    redirect_slashes=False,
    docs_url="/talos/docs" if env_dev else None,
    redoc_url="/talos/redoc" if env_dev else None,
    openapi_url="/talos/openapi.json" if env_dev else None,
    description="AI-powered Penetration Testing Agent",
)


app.add_middleware(JWTMiddleware)


@app.get("/talos/api", tags=["Welcome"])
async def welcome():
    return {"message": "Welcome to TalosAI API"}


app.include_router(
    tags=["Auth"],
    router=auth_router,
    prefix="/talos/api/auth",
)

app.include_router(
    tags=["Mission"],
    router=missions_router,
    prefix="/talos/api/missions",
    dependencies=[Depends(auth_scheme)]
)

app.include_router(
    tags=["Sessions"],
    router=sessions_router,
    prefix="/talos/api/sessions",
    dependencies=[Depends(auth_scheme)]
)

app.include_router(
    tags=["Status"],
    router=status_router,
    prefix="/talos/api/status",
    dependencies=[Depends(auth_scheme)]
)

app.include_router(
    tags=["Users"],
    router=users_router,
    prefix="/talos/api/users",
    dependencies=[Depends(auth_scheme)]
)
