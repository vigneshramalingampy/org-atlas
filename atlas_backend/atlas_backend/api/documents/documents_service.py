import hashlib
from pathlib import Path
import tempfile

from fastapi import BackgroundTasks, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger

from atlas_backend.modules.ingestion.model import IngestionJob, IngestionStatus
from atlas_backend.modules.ingestion.service import IngestionService
from atlas_backend.provider.storage.base import StorageProvider
from atlas_backend.schemas.document import JobStatusResponse, UploadResponse
from atlas_backend.utils.enums import FileType


class DocumentService:
    def __init__(
        self,
        ingestion_service: IngestionService | None = None,
        storage_provider: StorageProvider | None = None,
        bucket: str = "atlas-documents",
    ) -> None:
        self._jobs: dict[str, IngestionJob] = {}
        self._service = ingestion_service
        self._storage = storage_provider
        self._bucket = bucket

    def set_ingestion_service(self, service: IngestionService) -> None:
        self._service = service

    def set_storage_provider(self, storage: StorageProvider, bucket: str) -> None:
        self._storage = storage
        self._bucket = bucket

    def _resolve_file_type(self, filename: str) -> FileType | None:
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

    def _content_type(self, filename: str) -> str:
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

    def _compute_checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    async def _run_ingestion(
        self, job: IngestionJob, file_path: str, file_type: FileType
    ) -> None:
        logger.info("[{}] Starting background ingestion for {}", job.id, file_path)
        assert self._service is not None
        result = await self._service.ingest(file_path, file_type, document_id=job.id)
        job.status = result.status
        job.total_chunks = result.total_chunks
        job.error = result.error
        job.updated_at = result.updated_at
        logger.info(
            "[{}] Background ingestion complete: status={}, chunks={}",
            job.id,
            result.status.value,
            result.total_chunks,
        )

    async def upload_document(
        self, file: UploadFile, background_tasks: BackgroundTasks
    ) -> JSONResponse:
        if self._service is None:
            logger.warning("Upload rejected: ingestion service not initialized")
            return JSONResponse(
                status_code=503,
                content={"detail": "Ingestion service not initialized"},
            )

        if self._storage is None:
            logger.warning("Upload rejected: storage service not initialized")
            return JSONResponse(
                status_code=503,
                content={"detail": "Storage service not initialized"},
            )

        if not file.filename:
            logger.warning("Upload rejected: no filename")
            return JSONResponse(
                status_code=422,
                content={"detail": "No filename provided"},
            )

        file_type = self._resolve_file_type(file.filename)
        if file_type is None:
            logger.warning("Upload rejected: unsupported type {}", file.filename)
            return JSONResponse(
                status_code=422,
                content={"detail": f"Unsupported file type: {file.filename}"},
            )

        content = await file.read()
        checksum = self._compute_checksum(content)
        size_mb = len(content) / (1024 * 1024)

        logger.info(
            "Uploading: file={}, type={}, size={:.2f}MB",
            file.filename,
            file_type.value,
            size_mb,
        )

        job = IngestionJob(
            filename=file.filename,
            file_type=file_type.value,
            checksum=checksum,
        )

        storage_path = f"{job.id}/{file.filename}"
        await self._storage.upload(
            bucket=self._bucket,
            path=storage_path,
            data=content,
            content_type=self._content_type(file.filename),
        )
        job.storage_path = storage_path
        logger.info(
            "Uploaded to storage: bucket={}, path={}", self._bucket, storage_path
        )

        tmp_dir = Path(tempfile.mkdtemp(prefix="atlas_ingest_"))
        tmp_path = tmp_dir / file.filename
        tmp_path.write_bytes(content)

        self._jobs[job.id] = job

        background_tasks.add_task(self._run_ingestion, job, str(tmp_path), file_type)
        logger.info("Ingestion queued: job_id={}, file={}", job.id, file.filename)

        return JSONResponse(
            status_code=202,
            content=UploadResponse(
                job_id=job.id,
                status=job.status,
                filename=job.filename,
                file_type=job.file_type,
                checksum=job.checksum,
                storage_path=job.storage_path,
            ).model_dump(mode="json"),
        )

    def get_job_status(self, job_id: str) -> JSONResponse:
        job = self._jobs.get(job_id)
        if job is None:
            logger.warning("Job not found: {}", job_id)
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

        logger.debug("Job status: id={}, status={}", job_id, job.status.value)
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
            ).model_dump(mode="json"),
        )
