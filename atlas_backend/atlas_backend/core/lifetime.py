from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from atlas_backend.api.documents.documents_service import DocumentService
from atlas_backend.core.settings import settings
from atlas_backend.modules.ingestion.chunker.config import ChunkingConfig
from atlas_backend.modules.ingestion.service import IngestionService
from atlas_backend.provider.embedding.sentence_transformer import (
    SentenceTransformerProvider,
)
from atlas_backend.provider.knowledge.vector_store.surrealdb import (
    SurrealDBVectorStore,
)
from atlas_backend.provider.storage.supabase import SupabaseStorageProvider


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    storage = SupabaseStorageProvider(
        url=settings.supabase_url,
        anon_key=settings.supabase_anon_key,
    )
    document_service = DocumentService()
    document_service.set_storage_provider(storage, settings.supabase_bucket)

    embedding_provider = SentenceTransformerProvider(
        model_name=settings.embedding_model,
    )

    vector_store = SurrealDBVectorStore(
        url=settings.surrealdb_url,
        namespace=settings.surrealdb_namespace,
        database=settings.surrealdb_database,
        user=settings.surrealdb_user,
        password=settings.surrealdb_pass,
    )
    await vector_store.connect()

    chunking_config = ChunkingConfig(
        strategy=settings.chunking_strategy,
        max_chunk_size=settings.chunk_max_size,
        min_chunk_size=settings.chunk_min_size,
        parent_size=settings.chunk_parent_size,
        overlap=settings.chunk_overlap,
    )

    ingestion_service = IngestionService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        chunking_config=chunking_config,
    )
    document_service.set_ingestion_service(ingestion_service)

    # Make services available to route handlers via app.state
    app.state.document_service = document_service
    app.state.vector_store = vector_store
    app.state.embedding_provider = embedding_provider

    logger.info(
        "Ingestion pipeline ready (model={}, dim={}, storage=supabase)",
        embedding_provider.model_name,
        embedding_provider.dimensions,
    )

    yield

    logger.info("Shutting down...")
    await vector_store.close()
