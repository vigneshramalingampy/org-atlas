import enum

from pydantic_settings import BaseSettings


class LogLevel(enum.Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    ERROR = "ERROR"
    FATAL = "FATAL"
    WARNING = "WARNING"


class Settings(BaseSettings):
    environment: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8009
    reload: bool = True
    log_level: LogLevel = LogLevel.INFO

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_bucket: str = "atlas-documents"

    surrealdb_url: str = "ws://localhost:8000/rpc"
    surrealdb_namespace: str = "atlas"
    surrealdb_database: str = "knowledge"
    surrealdb_user: str = "root"
    surrealdb_pass: str = "root"

    chunking_strategy: str = "recursive"
    chunk_max_size: int = 512
    chunk_min_size: int = 100
    chunk_parent_size: int = 1024
    chunk_overlap: int = 0

    embedding_provider: str = "sentence-transformer-mini"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 64

    graph_extraction_enabled: bool = False
    graph_llm_provider: str = "ollama"

    chat_llm_provider: str = "ollama"
    chat_model: str
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    chat_temperature: float = 0.7
    chat_max_tokens: int = 1024
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.0

    max_file_size_mb: int = 50
    allowed_file_types: list[str] = ["pdf", "docx", "html", "md"]


settings = Settings()
