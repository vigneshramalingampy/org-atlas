from loguru import logging

from fastapi import APIRouter, BackgroundTasks, UploadFile
from fastapi.responses import JSONResponse

from atlas_backend.api.documents.service import DocumentService
from atlas_backend.schemas.document import JobStatusResponse, UploadResponse

logger = logging.getLogger(__name__)

documents_router = APIRouter(tags=["Documents"])


@documents_router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    upload_document = DocumentService()
    return await upload_document.upload_document(file, background_tasks)


@documents_router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JSONResponse:
    upload_document = DocumentService()
    return upload_document.get_job_status(job_id)
