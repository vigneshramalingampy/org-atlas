import hashlib
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, UploadFile
from fastapi.responses import JSONResponse

from atlas_backend.modules.ingestion.model import IngestionJob, IngestionStatus
from atlas_backend.modules.ingestion.service import IngestionService
from atlas_backend.provider.storage.base import StorageProvider
from atlas_backend.schemas.document import JobStatusResponse, UploadResponse
from atlas_backend.utils.enums import FileType

logger = logging.getLogger(__name__)

documents_router = APIRouter(tags=["Documents"])

_jobs: dict[str, IngestionJob] = {}
_service: IngestionService | None = None
_storage: StorageProvider | None = None
_bucket: str = "atlas-documents"


def set_ingestion_service(service: IngestionService) -> None:
    global _service
    _service = service


def set_storage_provider(storage: StorageProvider, bucket: str) -> None:
    global _storage, _bucket
    _storage = storage
    _bucket = bucket


def _resolve_file_type(filename: str) -> FileType | None:
    ext = Path(filename).suffix.lower().lstrip(".")
    mapping = {
        "pdf": FileType.PDF,
        "docx": FileType.DOCX,
        "doc": FileType.DOCX,
        "html": FileType.HTML,
        "htm": FileType.HTML,
        "md": FileType.MARKDOWN,
        "markdown": FileType.MARKDOWN,
    }
    return mapping.get(ext)


def _content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".html": "text/html",
        ".htm": "text/html",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
    }
    return types.get(ext, "application/octet-stream")


def _compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _run_ingestion(
    job: IngestionJob, file_path: str, file_type: FileType
) -> None:
    assert _service is not None
    result = await _service.ingest(file_path, file_type)
    job.status = result.status
    job.total_chunks = result.total_chunks
    job.error = result.error
    job.updated_at = result.updated_at


@documents_router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    if _service is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Ingestion service not initialized"},
        )

    if _storage is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Storage service not initialized"},
        )

    if not file.filename:
        return JSONResponse(
            status_code=422,
            content={"detail": "No filename provided"},
        )

    file_type = _resolve_file_type(file.filename)
    if file_type is None:
        return JSONResponse(
            status_code=422,
            content={"detail": f"Unsupported file type: {file.filename}"},
        )

    content = await file.read()
    checksum = _compute_checksum(content)

    job = IngestionJob(
        filename=file.filename,
        file_type=file_type.value,
        checksum=checksum,
    )

    storage_path = f"{job.id}/{file.filename}"
    await _storage.upload(
        bucket=_bucket,
        path=storage_path,
        data=content,
        content_type=_content_type(file.filename),
    )
    job.storage_path = storage_path

    tmp_dir = Path(tempfile.mkdtemp(prefix="atlas_ingest_"))
    tmp_path = tmp_dir / file.filename
    tmp_path.write_bytes(content)

    _jobs[job.id] = job

    background_tasks.add_task(_run_ingestion, job, str(tmp_path), file_type)

    return JSONResponse(
        status_code=202,
        content=UploadResponse(
            job_id=job.id,
            status=job.status,
            filename=job.filename,
            file_type=job.file_type,
            checksum=job.checksum,
            storage_path=job.storage_path,
        ).model_dump(),
    )


@documents_router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JSONResponse:
    job = _jobs.get(job_id)
    if job is None:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Job not found: {job_id}"},
        )

    progress = None
    if job.status not in (
        IngestionStatus.COMPLETED,
        IngestionStatus.FAILED,
        IngestionStatus.PENDING,
    ):
        progress = {
            "stage": job.status.value,
            "total_chunks": job.total_chunks,
        }

    return JSONResponse(
        status_code=200,
        content=JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=progress,
            total_chunks=job.total_chunks,
            error=job.error,
            storage_path=job.storage_path,
            created_at=job.created_at,
            updated_at=job.updated_at,
        ).model_dump(),
    )
