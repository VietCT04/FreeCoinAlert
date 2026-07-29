from fastapi import APIRouter

from freecoinalert_api.api.routes.auth import auth_router
from freecoinalert_api.api.routes.health import health_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
