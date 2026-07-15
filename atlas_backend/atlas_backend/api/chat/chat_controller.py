from fastapi import APIRouter, Request
from loguru import logger

from atlas_backend.api.chat.chat_service import ChatService
from atlas_backend.schemas.chat import ChatRequest, ChatResponse

chat_router = APIRouter(tags=["Chat"])


@chat_router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    chat_service: ChatService = request.app.state.chat_service
    logger.debug("POST /chat/ query='{}'", body.query[:100])
    return await chat_service.chat(body)
