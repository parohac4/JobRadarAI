from fastapi import APIRouter

from app.api.v1 import aggregator, auth, system

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(aggregator.router, prefix="/aggregate", tags=["aggregate"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
