from fastapi import APIRouter
from fastapi.responses import JSONResponse


health_router = APIRouter(tags=["Health"])

@health_router.get("/")
async def health():
    return JSONResponse(status_code=200,
                    content={"status": "Ping Pong!!!"})