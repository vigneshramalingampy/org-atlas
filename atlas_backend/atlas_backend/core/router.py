from fastapi import APIRouter
from atlas_backend.api.health.controller import health_router

core_router = APIRouter()

core_router.include_router(health_router, prefix="/health")
