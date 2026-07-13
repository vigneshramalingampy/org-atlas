from fastapi import APIRouter

from atlas_backend.api.documents.documents_controller import documents_router
from atlas_backend.api.health.health_controller import health_router

core_router = APIRouter()

core_router.include_router(health_router, prefix="/health")
core_router.include_router(documents_router, prefix="/documents")
