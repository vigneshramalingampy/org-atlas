# Atlas Backend

Backend service for **Atlas**, a Retrieval-Augmented Generation (RAG) platform for querying organizational knowledge. Ingests PDF/DOCX/HTML/Markdown documents, stores vector embeddings in SurrealDB, and answers questions via LLM.

---

## Tech Stack

- **Python 3.13** — Runtime
- **FastAPI** — REST API framework
- **SurrealDB 2.x** — Vector store with HNSW cosine similarity search
- **Supabase Storage** — Raw document file storage
- **all-MiniLM-L6-v2** — Sentence transformer embeddings (384 dims)
- **Ollama / OpenAI / DeepSeek / Anthropic** — LLM providers
- **pymupdf / BeautifulSoup / mistune / python-docx** — Document extractors

---

## Prerequisites

- Python **3.13**+
- [SurrealDB 2.x](https://surrealdb.com/install) running locally
- [Ollama](https://ollama.com/) (if using Ollama provider) with at least one model pulled
- A [Supabase](https://supabase.com/) project (for document storage)

---

## Getting Started

### 1. Clone and install

```bash
git clone <repository-url>
cd atlas_backend
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt   # or use uv
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### 3. Start SurrealDB

```bash
surreal start --user root --pass root memory
```

### 4. Run the server

```bash
python -m atlas_backend
```

Server starts at `http://localhost:8009` with auto-reload.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `dev` | Runtime environment |
| `HOST` | `localhost` | Server host |
| `PORT` | `8009` | Server port |
| **Supabase** | | |
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | — | Supabase anon/public key |
| `SUPABASE_BUCKET` | `atlas-documents` | Storage bucket name |
| **SurrealDB** | | |
| `SURREALDB_URL` | `ws://127.0.0.1:8000/rpc` | WebSocket endpoint |
| `SURREALDB_NAMESPACE` | `atlas` | SurrealDB namespace |
| `SURREALDB_DATABASE` | `knowledge` | SurrealDB database |
| **Chunking** | | |
| `CHUNKING_STRATEGY` | `recursive` | Chunking algorithm |
| `CHUNK_MAX_SIZE` | `512` | Max chunk size |
| `CHUNK_MIN_SIZE` | `100` | Min chunk size |
| `CHUNK_OVERLAP` | `0` | Chunk overlap |
| **Embedding** | | |
| `EMBEDDING_PROVIDER` | `sentence-transformer-mini` | Embedding provider |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model |
| `EMBEDDING_BATCH_SIZE` | `64` | Embedding batch size |
| **LLM / Chat** | | |
| `CHAT_LLM_PROVIDER` | `ollama` | LLM provider (`ollama`, `openai`, `deepseek`, `anthropic`) |
| `CHAT_MODEL` | `llama3.1` | Model name for the provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `CHAT_TEMPERATURE` | `0.7` | LLM temperature |
| `CHAT_MAX_TOKENS` | `1024` | Max tokens per response |
| `RETRIEVAL_TOP_K` | `5` | Number of chunks to retrieve |
| `RETRIEVAL_MIN_SCORE` | `0.0` | Minimum similarity score threshold |
| **Upload** | | |
| `MAX_FILE_SIZE_MB` | `50` | Max upload file size |
| `ALLOWED_FILE_TYPES` | `["pdf","docx","html","md"]` | Accepted file types |

---

## API Endpoints

### `GET /api/v1/health/`

Health check.

### `POST /api/v1/documents/upload`

Upload a document for ingestion.

```bash
curl -X POST http://localhost:8009/api/v1/documents/upload \
  -F "file=@document.pdf"
```

Returns `202 Accepted` with a `job_id`:

```json
{
  "job_id": "5392d512-1d65-493b-9121-2d3c01e83411",
  "status": "pending",
  "filename": "document.pdf",
  "file_type": "pdf",
  "checksum": "abc123...",
  "storage_path": "5392d512-.../document.pdf"
}
```

### `GET /api/v1/documents/{job_id}/status`

Check ingestion status:

```bash
curl http://localhost:8009/api/v1/documents/5392d512-.../status
```

### `POST /api/v1/chat/`

Ask a question based on ingested documents.

```bash
curl -X POST http://localhost:8009/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Kubernetes?", "top_k": 3}'
```

Optionally scope to a specific document:

```json
{
  "query": "What is Kubernetes?",
  "document_id": "5392d512-1d65-493b-9121-2d3c01e83411",
  "top_k": 3
}
```

Response:

```json
{
  "answer": "Kubernetes is a container orchestration platform...",
  "sources": [
    {
      "chunk_id": "chunks:abc...",
      "source": "Kubernetes-for-Beginners.pdf",
      "page": 2,
      "score": 0.92,
      "text_preview": "Kubernetes is an open-source system..."
    }
  ]
}
```

---

## Pipeline Architecture

```
Upload → Supabase Storage
  │
  └─ Background Task ──→ Extractor (PDF/DOCX/HTML/MD)
                           │
                           ▼
                         Cleaner
                           │
                           ▼
                         Chunker (Recursive)
                           │
                           ▼
                         Embedder (all-MiniLM-L6-v2)
                           │
                           ▼
                         SurrealDB Vector Store (HNSW cosine)

Chat Request → Retriever → Embed Query → Vector Search
                │
                ▼
              PromptBuilder (context + query)
                │
                ▼
              LLM (Ollama/OpenAI/DeepSeek/Anthropic)
                │
                ▼
              Response + Sources
```

---

## Project Structure

```text
atlas_backend/
├── __main__.py                      # Uvicorn entrypoint
├── api/
│   ├── chat/                        # Chat endpoint
│   │   ├── chat_controller.py
│   │   └── chat_service.py
│   ├── documents/                   # Upload + status
│   │   ├── documents_controller.py
│   │   └── documents_service.py
│   └── health/                      # Health check
│       └── health_controller.py
├── core/
│   ├── application.py               # FastAPI app factory
│   ├── lifetime.py                  # Lifespan (wires services)
│   ├── router.py                    # Route aggregation
│   └── settings.py                  # Pydantic settings
├── modules/
│   ├── ingestion/                   # Document → Chunks pipeline
│   │   ├── model.py                 # IngestionJob, IngestionStatus
│   │   ├── service.py               # Orchestrator
│   │   ├── extractor/               # PDF, DOCX, HTML, MD
│   │   ├── chunker/                 # Text chunking
│   │   ├── cleaner/                 # Text cleaning
│   │   └── embedder/                # Embedding service
│   ├── retrival/                    # Vector search retrieval
│   │   └── retriver.py
│   └── generation/                  # Prompt construction
│       └── prompt_builder.py
├── provider/
│   ├── embedding/                   # Sentence transformers
│   ├── llm/                         # Ollama, OpenAI, DeepSeek, Anthropic
│   ├── storage/                     # Supabase storage
│   └── knowledge/
│       └── vector_store/            # SurrealDB vector store
├── schemas/                         # Pydantic models
└── utils/
    └── enums.py                     # LLMModel, FileType
```
