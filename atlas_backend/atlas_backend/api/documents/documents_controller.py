from loguru import logger

from fastapi import APIRouter, BackgroundTasks, Request, UploadFile
from fastapi.responses import JSONResponse

from atlas_backend.schemas.document import JobStatusResponse, UploadResponse

documents_router = APIRouter(tags=["Documents"])


@documents_router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    request: Request,
) -> JSONResponse:
    logger.info("Upload request: filename={}", file.filename)
    document_service = request.app.state.document_service
    return await document_service.upload_document(file, background_tasks)


@documents_router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, request: Request) -> JSONResponse:
    logger.info("Job status request: job_id={}", job_id)
    document_service = request.app.state.document_service
    return await document_service.get_job_status(job_id)
