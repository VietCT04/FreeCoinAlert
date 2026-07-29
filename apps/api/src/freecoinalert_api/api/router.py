from fastapi import APIRouter

from freecoinalert_api.api.routes.auth import auth_router
from freecoinalert_api.api.routes.health import health_router
from freecoinalert_api.api.routes.markets import markets_router
from freecoinalert_api.api.routes.telegram import telegram_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(markets_router)
api_router.include_router(telegram_router)
