from fastapi import Depends, FastAPI

from app.api.deps import auth_scheme
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.missions import router as missions_router
from app.api.endpoints.status import router as status_router
from app.api.endpoints.users import router as users_router
from app.core.middleware import JWTMiddleware


app = FastAPI(
    version="0.1.0",
    title="TalosAI API",
    redirect_slashes=False,
    docs_url="/talos/docs",
    redoc_url="/talos/redoc",
    openapi_url="/talos/openapi.json",
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
