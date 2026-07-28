from loguru import logger
from surrealdb import AsyncSurreal

from atlas_backend.modules.ingestion.model import IngestionJob, IngestionStatus
from atlas_backend.provider.job_store.base import JobStore

JOBS_TABLE = "jobs"


class SurrealDBJobStore(JobStore):
    def __init__(
        self,
        url: str,
        namespace: str,
        database: str,
        user: str = "root",
        password: str = "root",
    ) -> None:
        self._url = url
        self._namespace = namespace
        self._database = database
        self._user = user
        self._password = password
        self._client = AsyncSurreal(url)

    async def connect(self) -> None:
        await self._client.connect()
        await self._client.signin({"user": self._user, "pass": self._password})
        await self._client.use(self._namespace, self._database)
        logger.info("Connected to SurrealDB job store at {}", self._url)

    async def initialize(self) -> None:
        await self._client.query(
            f"""
            DEFINE TABLE IF NOT EXISTS {JOBS_TABLE} SCHEMAFULL;
            DEFINE FIELD IF NOT EXISTS job_id ON {JOBS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS status ON {JOBS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS filename ON {JOBS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS file_type ON {JOBS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS checksum ON {JOBS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS storage_path ON {JOBS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS total_chunks ON {JOBS_TABLE} TYPE option<int>;
            DEFINE FIELD IF NOT EXISTS error ON {JOBS_TABLE} TYPE option<string>;
            DEFINE FIELD IF NOT EXISTS created_at ON {JOBS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS updated_at ON {JOBS_TABLE} TYPE string;
            DEFINE INDEX IF NOT EXISTS idx_job_id ON {JOBS_TABLE} FIELDS job_id UNIQUE;
            """
        )
        logger.info("Initialized SurrealDB jobs table")

    async def save(self, job: IngestionJob) -> None:
        existing = await self._client.query(
            f"SELECT id FROM {JOBS_TABLE} WHERE job_id = $job_id",
            {"job_id": job.id},
        )

        data = {
            "job_id": job.id,
            "status": job.status.value,
            "filename": job.filename,
            "file_type": job.file_type,
            "checksum": job.checksum,
            "storage_path": job.storage_path,
            "total_chunks": job.total_chunks,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }

        if existing and len(existing) > 0 and existing[0].get("id"):
            record_id = existing[0]["id"]
            await self._client.merge(record_id, data)
        else:
            await self._client.create(JOBS_TABLE, data)

    async def get(self, job_id: str) -> IngestionJob | None:
        results = await self._client.query(
            f"SELECT * FROM {JOBS_TABLE} WHERE job_id = $job_id",
            {"job_id": job_id},
        )

        if not results or len(results) == 0:
            return None

        record = results[0]
        if not isinstance(record, dict):
            return None

        return IngestionJob(
            id=record.get("job_id", job_id),
            status=IngestionStatus(record.get("status", "pending")),
            filename=record.get("filename", ""),
            file_type=record.get("file_type", ""),
            checksum=record.get("checksum", ""),
            storage_path=record.get("storage_path", ""),
            total_chunks=record.get("total_chunks"),
            error=record.get("error"),
        )

    async def close(self) -> None:
        await self._client.close()
