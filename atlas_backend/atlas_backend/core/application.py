"""application starting file"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from atlas_backend.health.controller import health_router

from atlas_backend.core.lifetime import lifespan

def app() -> FastAPI:

    fastapi_app = FastAPI(
        title="Atlas-Backend",
        summary="Atlas-Backend API Specification",
        description="Backend service for the RAG based org atlas",
        docs_url="/api/v1/docs",
        # redoc_url=None,
        # openapi_url="/openapi.json",
        lifespan=lifespan
    )

    allowed_origin = [
        "http://localhost:8000",
        "http://localhost:3000"
    ]

    fastapi_app.add_middleware(CORSMiddleware,
                               allow_origins = allowed_origin,
                               allow_methods = ["*"],
                               allow_headers = ["*"]
                               )
    fastapi_app.include_router(prefix="/api/v1/health", router=health_router)
    return fastapi_app
