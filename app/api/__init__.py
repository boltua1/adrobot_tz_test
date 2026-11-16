from fastapi import APIRouter
from app.api.campaigns import router as campaigns_router
from app.api.streams import router as streams_router
from app.api.offers import router as offers_router
from app.api.resources import router as resources_router

api_router = APIRouter(prefix="/api")
api_router.include_router(campaigns_router)
api_router.include_router(streams_router)
api_router.include_router(offers_router)
api_router.include_router(resources_router)
