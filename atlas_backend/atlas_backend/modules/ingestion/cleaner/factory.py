from atlas_backend.modules.ingestion.cleaner.base import DocumentCleaner
from atlas_backend.modules.ingestion.cleaner.default import DefaultCleaner


class CleanerFactory:
    _registry: dict[str, type[DocumentCleaner]] = {
        "default": DefaultCleaner,
    }

    @classmethod
    def create(cls, strategy: str = "default") -> DocumentCleaner:
        cleaner_cls = cls._registry.get(strategy)
        if cleaner_cls is None:
            raise ValueError(f"Unsupported cleaning strategy: {strategy}")
        return cleaner_cls()
