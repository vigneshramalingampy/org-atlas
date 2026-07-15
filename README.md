# Org Atlas

> **Ask your organization anything.**

Org Atlas is an AI-powered enterprise knowledge platform that enables organizations to upload internal documents and interact with them using natural language. It leverages Retrieval-Augmented Generation (RAG) to provide accurate, context-aware responses grounded in your organization's knowledge base.

> ⚠️ **Project Status:** Phase 1 (MVP) – Active Development

---

## Overview

Org Atlas demonstrates how modern AI can transform organizational knowledge into an intelligent assistant.

The initial version focuses on:

- 📄 Uploading documents
- ⚡ Processing and indexing content
- 💬 Chatting with uploaded knowledge
- 📚 Returning answers with citations
- 🐳 One-command local development using Docker

---

## Repository Structure

```text
org-atlas/
│
├── atlas_backend/         # Backend API & RAG Engine
├── atlas_frontend/        # Web Application
│
├── README.md
└── ROADMAP.md
```

---

## Tech Stack

### Backend

- Python 3.13
- FastAPI + Uvicorn
- SurrealDB 2.x (vector store with HNSW cosine)
- Supabase Storage (document file storage)
- Sentence Transformers (all-MiniLM-L6-v2, 384-dim embeddings)
- Ollama / OpenAI / DeepSeek / Anthropic (LLM providers)
- pymupdf / BeautifulSoup / mistune / python-docx (document extractors)

### Frontend

- React
- TypeScript
- Vite
- TailwindCSS

### AI

- Retrieval-Augmented Generation (RAG)
- Vector Embeddings
- Semantic Search
- Streaming Responses

---

## Phase 1 Features

- User-friendly chat interface
- Document upload (PDF, DOCX, HTML, Markdown)
- Upload progress tracking
- Automatic document processing (extract → clean → chunk → embed)
- Vector indexing (SurrealDB HNSW cosine similarity)
- AI-powered question answering with source citations
- Multiple LLM providers (Ollama, OpenAI, DeepSeek, Anthropic)

---

## Getting Started

### Prerequisites

- Python **3.13**+
- [SurrealDB 2.x](https://surrealdb.com/install) running locally
- [Ollama](https://ollama.com/) (if using Ollama LLM provider)
- A [Supabase](https://supabase.com/) project

### Backend setup

```bash
cd atlas_backend
cp .env.example .env        # edit with your credentials
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Start SurrealDB, then run:

```bash
python -m atlas_backend
```

Server starts at `http://localhost:8009`. Full setup details in [`atlas_backend/README.md`](atlas_backend/README.md).

### Frontend setup

```bash
cd atlas_frontend
```

Frontend-specific setup is documented inside its own README.

---

## Development

See the respective sub-project README for detailed setup and architecture:

- **[`atlas_backend/README.md`](atlas_backend/README.md)** — API, RAG pipeline, vector store, LLM providers
- **`atlas_frontend/README.md`** — Web application UI

---

## Project Roadmap

### ✅ Phase 1

- Chat interface
- Document upload
- Progress tracking
- RAG pipeline
- Basic citations

### 🚧 Phase 2

- Multiple document support
- Knowledge library
- Document management
- Search

### 🚧 Phase 3

- Authentication
- User profiles
- Chat history
- Workspaces

### 🚧 Phase 4

- Team collaboration
- Role-based access
- Admin dashboard

### 🚧 Phase 5

- Enterprise connectors
- Google Drive
- SharePoint
- Notion
- Slack

### 🚧 Future

- AI Agents
- Workflow automation
- Knowledge Graph
- Analytics
- Hybrid Search
- Production deployment

---

## Vision

Org Atlas aims to become an enterprise AI knowledge platform that helps organizations discover, understand, and interact with their internal knowledge through natural language.

---

## License

This project is licensed under the MIT License.
