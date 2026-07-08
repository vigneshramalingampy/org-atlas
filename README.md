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
├── backend/              # Backend API & RAG Engine
├── frontend/             # Web Application
│
├── docker/               # Docker configuration
├── docs/                 # Documentation
├── scripts/              # Helper scripts
│
├── docker-compose.yml
├── .env.example
├── README.md
└── ROADMAP.md
```

---

## Tech Stack

### Backend

- Python
- FastAPI
- PostgreSQL
- Qdrant
- Redis
- Ollama / OpenAI
- Docker

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
- Document upload
- Upload progress tracking
- Automatic document processing
- Vector indexing
- AI-powered question answering
- Source citations
- Docker-based local development

---

## Getting Started

### Clone the repository

```bash
git clone https://github.com/<your-org>/org-atlas.git
cd org-atlas
```

### Configure environment variables

```bash
cp .env.example .env
```

Update the required values inside `.env`.

---

### Start the application

```bash
docker compose up --build
```

---

### Access the application

| Service | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

---

## Development

### Backend

```bash
cd backend
```

Backend-specific setup instructions will be documented inside the backend directory.

---

### Frontend

```bash
cd frontend
```

Frontend-specific setup instructions will be documented inside the frontend directory.

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
