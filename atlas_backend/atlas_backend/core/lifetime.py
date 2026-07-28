from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from atlas_backend.api.chat.chat_service import ChatService
from atlas_backend.api.documents.documents_service import DocumentService
from atlas_backend.core.settings import settings
from atlas_backend.modules.ingestion.chunker.config import ChunkingConfig
from atlas_backend.modules.ingestion.graph.llm_extractor import LLMGraphExtractor
from atlas_backend.modules.ingestion.service import IngestionService
from atlas_backend.modules.retrival.query_router import QueryRouter
from atlas_backend.modules.retrival.retriver import Retriever
from atlas_backend.provider.embedding.sentence_transformer import (
    SentenceTransformerProvider,
)
from atlas_backend.provider.job_store.surrealdb import SurrealDBJobStore
from atlas_backend.provider.knowledge.graph_store.surrealdb import SurrealDBGraphStore
from atlas_backend.provider.knowledge.vector_store.surrealdb import (
    SurrealDBVectorStore,
)
from atlas_backend.provider.llm.base import LLMFactory
from atlas_backend.provider.storage.supabase import SupabaseStorageProvider


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    storage = SupabaseStorageProvider(
        url=settings.supabase_url,
        anon_key=settings.supabase_anon_key,
    )

    job_store = SurrealDBJobStore(
        url=settings.surrealdb_url,
        namespace=settings.surrealdb_namespace,
        database=settings.surrealdb_database,
        user=settings.surrealdb_user,
        password=settings.surrealdb_pass,
    )
    await job_store.connect()
    await job_store.initialize()

    document_service = DocumentService(job_store=job_store)
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

    graph_store = SurrealDBGraphStore(
        url=settings.surrealdb_url,
        namespace=settings.surrealdb_namespace,
        database=settings.surrealdb_database,
        user=settings.surrealdb_user,
        password=settings.surrealdb_pass,
    )
    await graph_store.connect()

    graph_extractor = None
    if settings.graph_extraction_enabled:
        graph_llm_provider = LLMFactory.create(
            settings.graph_llm_provider,
            api_key=getattr(settings, f"{settings.graph_llm_provider}_api_key", ""),
            base_url=settings.ollama_base_url,
        )
        graph_extractor = LLMGraphExtractor(llm_provider=graph_llm_provider)
        logger.info(
            "Graph extraction enabled (provider={})", settings.graph_llm_provider
        )

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
        graph_extractor=graph_extractor,
        graph_store=graph_store if settings.graph_extraction_enabled else None,
    )
    document_service.set_ingestion_service(ingestion_service)

    # -- Chat pipeline --
    api_key_map = {
        "openai": settings.openai_api_key,
        "deepseek": settings.deepseek_api_key,
        "anthropic": settings.anthropic_api_key,
    }
    llm_provider = LLMFactory.create(
        settings.chat_llm_provider,
        api_key=api_key_map.get(settings.chat_llm_provider, ""),
        base_url=settings.ollama_base_url,
    )
    retriever = Retriever(
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        graph_store=graph_store if settings.graph_extraction_enabled else None,
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
    )
    query_router = QueryRouter(
        llm_provider=llm_provider,
        model=settings.chat_model,
        graph_enabled=settings.graph_extraction_enabled,
    )
    chat_service = ChatService(
        retriever=retriever,
        llm_provider=llm_provider,
        query_router=query_router,
        temperature=settings.chat_temperature,
        max_tokens=settings.chat_max_tokens,
        model=settings.chat_model,
    )

    # Make services available to route handlers via app.state
    app.state.document_service = document_service
    app.state.vector_store = vector_store
    app.state.graph_store = graph_store
    app.state.embedding_provider = embedding_provider
    app.state.chat_service = chat_service

    logger.info(
        "Ingestion pipeline ready (model={}, dim={}, storage=supabase, graph={})",
        embedding_provider.model_name,
        embedding_provider.dimensions,
        "enabled" if settings.graph_extraction_enabled else "disabled",
    )
    logger.info(
        "Chat pipeline ready (llm={}, model={}, router=llm)",
        settings.chat_llm_provider,
        settings.chat_model,
    )

    yield

    logger.info("Shutting down...")
    await vector_store.close()
    await graph_store.close()
    await job_store.close()
