# Atlas Backend — Ingestion Pipeline Architecture

> Version: 1.0
> Status: Draft
> Last Updated: 2026-07-12

---

## 1. Overview

Atlas is a Retrieval-Augmented Generation (RAG) platform for querying organizational knowledge. The ingestion pipeline transforms raw documents (PDF, DOCX, HTML, Markdown) into searchable, embeddable chunks stored in SurrealDB, with optional knowledge graph extraction for relationship-aware retrieval.

### Design Principles

- **Strategy + Factory pattern** — every stage is swappable behind an ABC, consistent with the existing extractor architecture
- **Async-first** — all pipeline stages are async for non-blocking I/O
- **Format-aware** — chunking respects document structure (headings, pages, tables)
- **Hierarchical retrieval** — small chunks for precise matching, large chunks for generation context
- **Progressive enhancement** — start with vector RAG, add graph extraction later without rearchitecting

---

## 2. Pipeline Flow

```
POST /documents/upload
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│                    IngestionService                            │
│              (orchestrator — modules/ingestion/service.py)     │
│                                                                │
│  1. Validate file type, checksum, size                         │
│  2. Create ingestion job (status: PENDING)                     │
│  3. Dispatch to background worker                              │
└───────────────────┬───────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 1: EXTRACT                                              │
│  modules/ingestion/extractor/                                  │
│                                                                │
│  Input:  file_path (str)                                       │
│  Output: ParsedDocument { metadata, pages[] }                  │
│                                                                │
│  ExtractorFactory.create(file_type) → DocumentExtractor        │
│  Extractors: PdfExtractor, DocxExtractor,                      │
│              HtmlExtractor, MarkdownExtractor                   │
└───────────────────┬───────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 2: CLEAN                                                │
│  modules/ingestion/cleaner/                                    │
│                                                                │
│  Input:  ParsedDocument                                        │
│  Output: ParsedDocument (cleaned)                              │
│                                                                │
│  - Normalize unicode and whitespace                            │
│  - Remove control characters and artifacts                     │
│  - Collapse multiple blank lines                               │
│  - Strip leading/trailing whitespace per page                  │
│  - Preserve structure (headings, tables, code blocks)          │
└───────────────────┬───────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 3: CHUNK                                               │
│  modules/ingestion/chunker/                                    │
│                                                                │
│  Input:  ParsedDocument (cleaned)                              │
│  Output: list[Chunk] with parent-child linking                 │
│                                                                │
│  Two-pass strategy:                                            │
│    Pass 1: Structure-aware macro splitting                     │
│            (by headings, pages, sections)                       │
│    Pass 2: Recursive micro splitting                           │
│            (paragraphs → sentences → characters)                │
│    Pass 3: Parent-child linking                                │
│            (micro chunks → parent macro chunks)                 │
└───────────────────┬───────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 4: EMBED                                               │
│  modules/ingestion/embedder/  +  provider/embedding/          │
│                                                                │
│  Input:  list[Chunk]                                           │
│  Output: list[Chunk] (with embedding vectors attached)         │
│                                                                │
│  EmbeddingProvider.generate(texts[]) → vectors[]               │
│  Providers: SentenceTransformerProvider (local)                │
│             OpenAIEmbeddingProvider (API) — future              │
│  Batch processing with retry and rate limiting                 │
└───────────────────┬───────────────────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│  STAGE 5a:       │ │  STAGE 5b:       │
│  VECTOR STORE    │ │  GRAPH EXTRACT   │
│  (required)      │ │  (optional)      │
│                  │ │                  │
│  Write chunks +  │ │  LLM-based       │
│  embeddings to   │ │  entity/relation  │
│  SurrealDB       │ │  extraction      │
│                  │ │  → SurrealDB     │
│                  │ │    graph store   │
└──────────────────┘ └──────────────────┘
          │                   │
          └─────────┬─────────┘
                    ▼
          Update job status → COMPLETED
```

---

## 3. Data Models

### 3.1 Extraction Models (existing)

Defined in `modules/ingestion/extractor/model.py`:

```python
@dataclass(slots=True)
class DocumentMetadata:
    filename: str
    total_pages: int
    file_type: str

@dataclass(slots=True)
class DocumentPage:
    page_number: int
    text: str

@dataclass(slots=True)
class ParsedDocument:
    metadata: DocumentMetadata
    pages: list[DocumentPage] = field(default_factory=list)
```

### 3.2 Chunk Models

To be defined in `modules/ingestion/chunker/model.py`:

```python
@dataclass(slots=True)
class ChunkMetadata:
    source: str              # original filename
    page: int | None         # page number (PDF), None for others
    section: str | None      # heading/section title if detected
    file_type: str           # pdf, docx, html, md
    char_count: int          # character count of chunk text
    token_count: int         # estimated token count

@dataclass(slots=True)
class Chunk:
    id: str                  # UUID, unique identifier
    text: str                # chunk content
    index: int               # position within document
    parent_id: str | None    # parent macro chunk ID (for hierarchical retrieval)
    child_ids: list[str]     # child micro chunk IDs
    metadata: ChunkMetadata  # source and structural context
```

### 3.3 Ingestion Job Model

To be defined in `modules/ingestion/model.py` or `schemas/`:

```python
class IngestionStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass(slots=True)
class IngestionJob:
    id: str                  # UUID
    document_id: str         # reference to stored document
    status: IngestionStatus
    file_type: str
    checksum: str            # SHA-256 of uploaded file (idempotency)
    total_chunks: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime
```

### 3.4 Stored Document Model (SurrealDB)

```surql
-- Document record
DEFINE TABLE document SCHEMAFULL;
DEFINE FIELD filename ON document TYPE string;
DEFINE FIELD file_type ON document TYPE string;
DEFINE FIELD checksum ON document TYPE string;
DEFINE FIELD total_pages ON document TYPE int;
DEFINE FIELD total_chunks ON document TYPE int;
DEFINE FIELD created_at ON document TYPE datetime;
DEFINE FIELD embedding_model ON document TYPE string;
DEFINE INDEX unique_checksum ON document FIELDS checksum UNIQUE;

-- Chunk record
DEFINE TABLE chunk SCHEMAFULL;
DEFINE FIELD text ON chunk TYPE string;
DEFINE FIELD index ON chunk TYPE int;
DEFINE FIELD parent_id ON chunk TYPE option<record<chunk>>;
DEFINE FIELD child_ids ON chunk TYPE array;
DEFINE FIELD source ON chunk TYPE string;
DEFINE FIELD page ON chunk TYPE option<int>;
DEFINE FIELD section ON chunk TYPE option<string>;
DEFINE FIELD file_type ON chunk TYPE string;
DEFINE FIELD char_count ON chunk TYPE int;
DEFINE FIELD token_count ON chunk TYPE int;
DEFINE FIELD embedding ON chunk TYPE option<array<float>>;
DEFINE FIELD document ON chunk TYPE record<document>;
DEFINE INDEX idx_chunk_document ON chunk FIELDS document;
DEFINE INDEX idx_chunk_embedding ON chunk FIELDS embedding HNSW options {
    dimensions: 384,
    distance: cosine
};

-- Entity record (graph)
DEFINE TABLE entity SCHEMAFULL;
DEFINE FIELD name ON entity TYPE string;
DEFINE FIELD entity_type ON entity TYPE string;
DEFINE FIELD properties ON object;
DEFINE INDEX idx_entity_name ON entity FIELDS name;

-- Relationship record (graph)
DEFINE TABLE relationship SCHEMAFULL;
DEFINE FIELD source ON relationship TYPE record<entity>;
DEFINE FIELD target ON relationship TYPE record<entity>;
DEFINE FIELD relation_type ON relationship TYPE string;
DEFINE FIELD properties ON object;
DEFINE TABLE knowledge GRAPH FROM (source, target);
```

---

## 4. Stage Details

### 4.1 Extractor (DONE)

**Module**: `modules/ingestion/extractor/`
**Status**: Fully implemented

| Component | File | Purpose |
|---|---|---|
| ABC | `base.py` | `DocumentExtractor.extract(file_path) → ParsedDocument` |
| PDF | `pdf.py` | PyMuPDF page-by-page extraction |
| DOCX | `docx.py` | python-docx paragraphs + tables |
| HTML | `html.py` | BeautifulSoup + lxml, noise tag stripping |
| Markdown | `markdown.py` | mistune → BeautifulSoup two-hop |
| Factory | `factory.py` | `ExtractorFactory.create(FileType)` |
| Models | `model.py` | `ParsedDocument`, `DocumentPage`, `DocumentMetadata` |

### 4.2 Cleaner

**Module**: `modules/ingestion/cleaner/`
**Status**: To implement

**Purpose**: Normalize extracted text while preserving structure. The cleaner runs between extraction and chunking to ensure consistent input quality.

**Operations**:
- Unicode normalization (NFKC form)
- Remove control characters except newlines and tabs
- Collapse 3+ consecutive blank lines to 2
- Strip trailing whitespace per line
- Normalize line endings to `\n`
- Remove page headers/footers (heuristic: repeated text at top/bottom of consecutive pages)

**ABC**:
```python
class DocumentCleaner(ABC):
    @abstractmethod
    async def clean(self, document: ParsedDocument) -> ParsedDocument: ...
```

**Factory**: `DocumentCleanerFactory.create()` — returns the cleaner instance. Initially a single implementation; the ABC allows domain-specific cleaners later (e.g., `LegalDocumentCleaner`).

**Design note**: The cleaner modifies `DocumentPage.text` in place for each page, preserving page structure and metadata.

### 4.3 Chunker

**Module**: `modules/ingestion/chunker/`
**Status**: To implement

**Strategy**: Recursive + Parent-Child Hierarchy (two-pass)

**Pass 1 — Macro splitting (structure-aware)**:
- Split by page boundaries (leverages `DocumentPage` from extractor)
- Within each page, detect headings (text matching heading patterns per format)
- Split at heading boundaries
- Keep tables, code blocks, and list items as whole units
- Result: macro chunks (512-1024 tokens)

**Pass 2 — Micro splitting (recursive fallback)**:
- For macro chunks exceeding `max_chunk_size`, split recursively
- Separator chain: `\n\n` → `\n` → `. ` → ` ` → character
- Result: micro chunks (256-512 tokens)

**Pass 3 — Parent-child linking**:
- Each micro chunk gets a `parent_id` pointing to its macro chunk
- Each macro chunk accumulates `child_ids`
- Micro chunks are indexed for retrieval; macro chunks are returned to the LLM

**ABC**:
```python
class TextChunker(ABC):
    @abstractmethod
    async def chunk(self, document: ParsedDocument, config: ChunkingConfig) -> list[Chunk]: ...
```

**Factory**:
```python
class ChunkingFactory:
    _registry: dict[str, type[TextChunker]] = {
        "recursive": RecursiveChunker,
        # "semantic": SemanticChunker,  # future
    }

    @classmethod
    def create(cls, strategy: str = "recursive") -> TextChunker: ...
```

**Configuration**:
```python
@dataclass
class ChunkingConfig:
    strategy: str = "recursive"
    max_chunk_size: int = 512        # tokens
    min_chunk_size: int = 100        # tokens
    parent_size: int = 1024          # parent macro chunk target size
    overlap: int = 0                 # characters, start with 0
    separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " "])
    keep_tables_whole: bool = True
    keep_code_blocks_whole: bool = True
```

**Adding a new strategy** (e.g., semantic):
1. Create `modules/ingestion/chunker/semantic.py`
2. Implement `SemanticChunker(TextChunker)`
3. Add `"semantic": SemanticChunker` to `ChunkingFactory._registry`
4. No changes to service or pipeline code

### 4.4 Embedder

**Module**: `modules/ingestion/embedder/` + `provider/embedding/`
**Status**: To implement

**Purpose**: Generate embedding vectors for each chunk. Abstracted at two levels:
- `modules/ingestion/embedder/` — ingestion-specific orchestration (batching, retry, progress)
- `provider/embedding/` — provider-agnostic ABC with concrete implementations

**Provider ABC** (`provider/embedding/base.py`):
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...
```

**Providers**:

| Provider | Library | Model | Dimensions | Speed | When to Use |
|---|---|---|---|---|---|
| `SentenceTransformerProvider` | sentence-transformers | all-MiniLM-L6-v2 | 384 | Fast (local) | Default, no API cost |
| `SentenceTransformerProvider` | sentence-transformers | all-mpnet-base-v2 | 768 | Medium (local) | Higher quality, technical docs |
| `OpenAIEmbeddingProvider` | openai | text-embedding-3-small | 1536 | API call | Best quality, paid |

**Factory**:
```python
class EmbeddingProviderFactory:
    _registry: dict[str, type[EmbeddingProvider]] = {
        "sentence-transformer-mini": SentenceTransformerMiniLM,
        "sentence-transformer-mpnet": SentenceTransformerMPNet,
        # "openai-small": OpenAIEmbeddingSmall,  # future
    }

    @classmethod
    def create(cls, provider: str = "sentence-transformer-mini") -> EmbeddingProvider: ...
```

**Batching strategy**:
- Batch size: 64 texts per embedding call (configurable)
- Retry with exponential backoff on transient errors
- Validate output dimensions match provider specification
- Embed parent chunks separately (for parent-child retrieval)

### 4.5 Graph Extraction (Optional)

**Module**: `modules/ingestion/graph/`
**Status**: Phase 2 — implement after vector pipeline is working

**Purpose**: Extract entities and relationships from document text using an LLM, storing them in SurrealDB's graph model. This enables relationship-aware retrieval (multi-hop queries, compliance tracing).

**When to use**: Toggle per document or per ingestion job. Not blocking the vector pipeline.

**Pipeline**:
1. For each chunk, call LLM with extraction prompt
2. Parse structured output (entities + relationships)
3. Deduplicate entities (name + type matching)
4. Store entities and relationships in SurrealDB graph tables
5. Link chunks to their extracted entities

**Entity types** (organizational knowledge):
- `Person` — names, roles
- `Department` — organizational units
- `Policy` — policies, procedures, rules
- `Document` — source documents
- `Concept` — domain-specific terms
- `Date` — temporal references
- `Requirement` — compliance, regulations

**Relationship types**:
- `REPORTS_TO` — organizational hierarchy
- `GOVERNS` — policy applies to department/person
- `SUPERSEDES` — document versioning
- `REFERENCES` — cross-document links
- `PART_OF` — hierarchical containment

**LLM integration**: Uses existing `LLMProvider` ABC from `provider/llm/`. The graph module sends extraction prompts and parses structured JSON responses.

**Cost consideration**: LLM-based extraction costs ~$20-500 per full document corpus. Recommendation: extract graph data selectively for high-value documents, or use LazyGraphRAG approach (Microsoft) to reduce cost to 0.1%.

### 4.6 Storage

**Module**: `provider/knowledge/`
**Status**: To implement

**Vector store** (`provider/knowledge/vector_store/`):
```python
class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, collection: str, points: list[VectorPoint]) -> None: ...

    @abstractmethod
    async def search(
        self, collection: str, query_vector: list[float],
        limit: int = 10, filters: dict | None = None
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> None: ...
```

**Graph store** (`provider/knowledge/graph_store/`):
```python
class GraphStore(ABC):
    @abstractmethod
    async def add_entity(self, entity: Entity) -> str: ...

    @abstractmethod
    async def add_relationship(self, relationship: Relationship) -> str: ...

    @abstractmethod
    async def traverse(
        self, start_id: str, depth: int = 2,
        relation_types: list[str] | None = None
    ) -> Subgraph: ...

    @abstractmethod
    async def find_entity(self, name: str, entity_type: str | None = None) -> list[Entity]: ...
```

**Implementation**: SurrealDB for both vector and graph stores. SurrealQL handles vectors, documents, and graph relationships in a single engine.

**SurrealDB advantages for this architecture**:
- ACID transactions (atomic chunk + embedding writes)
- Native HNSW vector indexing
- Graph traversal via `KNOWLEDGE` table and graph clauses
- Single connection for all data operations
- SurrealQL for complex hybrid queries (vector + graph + filter)

---

## 5. API Design

### 5.1 Upload & Ingest

```
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Body:
  file: <binary>

Response 202 Accepted:
{
  "job_id": "uuid",
  "status": "pending",
  "filename": "policy_v2.pdf",
  "file_type": "pdf",
  "checksum": "sha256:abc123..."
}
```

### 5.2 Job Status

```
GET /api/v1/documents/{job_id}/status

Response 200 OK:
{
  "job_id": "uuid",
  "status": "chunking",
  "progress": {
    "stage": "chunking",
    "chunks_created": 42
  },
  "created_at": "2026-07-12T10:00:00Z",
  "updated_at": "2026-07-12T10:00:03Z"
}
```

### 5.3 Query (Retrieval — future)

```
POST /api/v1/query
Content-Type: application/json

Body:
{
  "query": "What is the travel reimbursement policy for engineering?",
  "filters": {
    "department": "engineering"
  },
  "top_k": 5
}

Response 200 OK:
{
  "answer": "...",
  "sources": [
    {
      "chunk_id": "uuid",
      "text": "...",
      "source": "travel_policy_v3.pdf",
      "page": 4,
      "section": "Reimbursement Limits",
      "score": 0.92
    }
  ]
}
```

---

## 6. Error Handling

### Pipeline-level

Each stage catches exceptions and wraps them in stage-specific errors:

```python
class IngestionError(Exception): ...
class ExtractionError(IngestionError): ...
class CleaningError(IngestionError): ...
class ChunkingError(IngestionError): ...
class EmbeddingError(IngestionError): ...
class StorageError(IngestionError): ...
class GraphExtractionError(IngestionError): ...
```

### Idempotency

- SHA-256 checksum of uploaded file
- If checksum matches an existing document, skip ingestion or return existing job
- On document replacement: delete old chunks before inserting new ones

### Retry strategy

- Embedding API calls: exponential backoff (3 retries, 1s/2s/4s)
- SurrealDB writes: retry on connection errors (2 retries)
- Graph extraction: skip on failure (non-blocking, graph is optional)
- On unrecoverable failure: mark job as FAILED with error message

---

## 7. Configuration

All pipeline configuration lives in `core/settings.py` via pydantic-settings:

```python
class Settings(BaseSettings):
    # Application
    environment: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level: LogLevel = LogLevel.INFO

    # SurrealDB
    surrealdb_url: str = "ws://localhost:8000/rpc"
    surrealdb_namespace: str = "atlas"
    surrealdb_database: str = "knowledge"

    # Chunking
    chunking_strategy: str = "recursive"
    chunk_max_size: int = 512
    chunk_min_size: int = 100
    chunk_parent_size: int = 1024
    chunk_overlap: int = 0

    # Embedding
    embedding_provider: str = "sentence-transformer-mini"
    embedding_batch_size: int = 64

    # Graph (Phase 2)
    graph_extraction_enabled: bool = False
    graph_llm_provider: str = "ollama"

    # Ingestion
    max_file_size_mb: int = 50
    allowed_file_types: list[str] = ["pdf", "docx", "html", "md"]
```

---

## 8. Module Mapping

How the pipeline maps to the existing codebase structure:

```
atlas_backend/
├── core/
│   └── settings.py              # Pipeline configuration
│
├── modules/
│   └── ingestion/
│       ├── service.py           # IngestionService (orchestrator)
│       ├── model.py             # IngestionJob, IngestionStatus
│       │
│       ├── extractor/           # ✅ DONE
│       │   ├── base.py          # DocumentExtractor ABC
│       │   ├── model.py         # ParsedDocument, DocumentPage
│       │   ├── factory.py       # ExtractorFactory
│       │   ├── pdf.py
│       │   ├── docx.py
│       │   ├── html.py
│       │   └── markdown.py
│       │
│       ├── cleaner/             # TO IMPLEMENT
│       │   ├── base.py          # DocumentCleaner ABC
│       │   ├── default.py       # DefaultCleaner
│       │   └── factory.py       # CleanerFactory
│       │
│       ├── chunker/             # TO IMPLEMENT
│       │   ├── base.py          # TextChunker ABC
│       │   ├── model.py         # Chunk, ChunkMetadata
│       │   ├── recursive.py     # RecursiveChunker (default)
│       │   ├── config.py        # ChunkingConfig
│       │   └── factory.py       # ChunkingFactory
│       │
│       ├── embedder/            # TO IMPLEMENT
│       │   ├── service.py       # EmbeddingService (batch orchestration)
│       │   └── factory.py       # EmbeddingServiceFactory
│       │
│       ├── graph/               # PHASE 2
│       │   ├── extractor.py     # GraphExtractor (LLM-based)
│       │   ├── schema.py        # Entity types, relationship types
│       │   └── service.py       # GraphService
│       │
│       └── (retriever/)         # FUTURE — retrieval module
│
├── provider/
│   ├── embedding/
│   │   ├── base.py              # EmbeddingProvider ABC
│   │   ├── sentence_transformer.py  # SentenceTransformerProvider
│   │   └── openai.py            # OpenAIEmbeddingProvider (future)
│   │
│   ├── knowledge/
│   │   ├── vector_store/
│   │   │   ├── base.py          # VectorStore ABC
│   │   │   └── surrealdb.py     # SurrealDBVectorStore
│   │   └── graph_store/
│   │       ├── base.py          # GraphStore ABC
│   │       └── surrealdb.py     # SurrealDBGraphStore
│   │
│   └── llm/
│       └── (existing)           # LLM providers for graph extraction
│
├── schemas/
│   ├── document.py              # Upload/request/response schemas
│   └── query.py                 # Query schemas (future)
│
└── api/
    └── documents/
        ├── __init__.py
        └── controller.py        # POST /upload, GET /status
```

---

## 9. Implementation Phases

### Phase 1: Core Pipeline (MVP)

**Goal**: Upload a document → get embedded chunks in SurrealDB

1. Implement `DocumentCleaner` + factory
2. Implement `TextChunker` (recursive) + `Chunk` model + factory
3. Implement `EmbeddingProvider` ABC + `SentenceTransformerProvider`
4. Implement `VectorStore` ABC + SurrealDB vector store
5. Implement `IngestionService` orchestrator
6. Implement upload + status API endpoints
7. Add `IngestionStatus` tracking

### Phase 2: Graph Extraction

**Goal**: Optional entity/relation extraction for relationship-aware retrieval

1. Define entity/relationship schemas
2. Implement `GraphExtractor` using LLM providers
3. Implement `GraphStore` ABC + SurrealDB graph store
4. Add graph extraction as parallel branch in ingestion pipeline
5. Add graph-aware queries

### Phase 3: Retrieval & Generation

**Goal**: Query the ingested knowledge

1. Implement retriever (vector similarity + optional graph traversal)
2. Implement reranker (cross-encoder)
3. Implement generation pipeline (retrieved context → LLM → answer)
4. Implement hybrid search (BM25 + vector via RRF)

### Phase 4: Production Hardening

**Goal**: Reliability, monitoring, scale

1. Add structured logging (loguru)
2. Add metrics (ingestion latency, chunk counts, embedding throughput)
3. Add document update/reindex support
4. Add multi-tenant support
5. Performance testing and optimization

---

## 10. Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Chunking** | Recursive + Parent-Child | Best balance of speed and quality; 2026 production consensus |
| **Embedding (default)** | Sentence Transformers (all-MiniLM-L6-v2) | Free, fast (local), 384 dimensions, good for MVP |
| **Embedding (quality)** | Sentence Transformers (all-mpnet-base-v2) | Higher quality, 768 dimensions, for technical docs |
| **Vector + Graph DB** | SurrealDB | Unified store, ACID, native HNSW + graph traversal, simpler ops |
| **Async processing** | FastAPI BackgroundTasks (MVP) → ARQ (production) | Start simple, migrate to task queue when retries/reliability needed |
| **Overlap** | Start at 0 | Jan 2026 research shows no measurable benefit; add only if metrics require |
| **Chunk size** | 512 tokens | Pragmatic default from 2026 benchmarks; tune based on retrieval eval |
| **Graph extraction** | Phase 2, optional | High cost, high value for org queries; don't block MVP vector pipeline |
