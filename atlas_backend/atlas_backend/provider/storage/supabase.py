import logging

from supabase import Client, create_client

from atlas_backend.provider.storage.base import StoredFile, StorageProvider

logger = logging.getLogger(__name__)


class SupabaseStorageProvider(StorageProvider):
    def __init__(self, url: str, anon_key: str) -> None:
        self._client: Client = create_client(url, anon_key)

    async def upload(
        self, bucket: str, path: str, data: bytes, content_type: str
    ) -> StoredFile:
        self._client.storage.from_(bucket).upload(
            file=data,
            path=path,
            file_options={"content-type": content_type, "upsert": "true"},
        )

        logger.info("Uploaded %s to %s/%s (%d bytes)", path, bucket, path, len(data))

        return StoredFile(
            path=path,
            bucket=bucket,
            size_bytes=len(data),
        )

    async def download(self, bucket: str, path: str) -> bytes:
        data = self._client.storage.from_(bucket).download(path)
        logger.info("Downloaded %s/%s (%d bytes)", bucket, path, len(data))
        return data

    async def delete(self, bucket: str, path: str) -> None:
        self._client.storage.from_(bucket).remove([path])
        logger.info("Deleted %s/%s", bucket, path)

    async def exists(self, bucket: str, path: str) -> bool:
        try:
            self._client.storage.from_(bucket).list(path)
            return True
        except Exception:
            return False
