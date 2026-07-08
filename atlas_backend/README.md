# Atlas Backend

Backend service powering **Atlas**, a Retrieval-Augmented Generation (RAG) platform for querying organizational knowledge.

---

## Features

- REST API backend
- Retrieval-Augmented Generation (RAG)
- Document ingestion pipeline
- Environment-based configuration
- Built with modern Python tooling

---

## Tech Stack

- Python 3.12+
- FastAPI
- Uvicorn
- uv (Astral package manager)

---

## Prerequisites

Before getting started, ensure you have:

- Python **3.12** or later
- **uv** package manager

Install `uv` if you don't already have it:

```bash
pip install uv
```

Or follow the official installation guide:

https://docs.astral.sh/uv/

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd atlas-backend
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Update the values in `.env` with your local configuration.

---

## Running the Application

Start the development server:

```bash
uv run python -m atlas_backend
```

---

## Project Structure

```text
atlas-backend/
├── atlas_backend/
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── models/
│   └── __main__.py
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Development

Synchronize dependencies after pulling changes:

```bash
uv sync
```

Run the application:

```bash
uv run python -m atlas_backend
```

---

## Environment Variables

Store all application configuration inside the `.env` file.

Example:

```env
APP_NAME=Atlas Backend
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

Refer to `.env.example` for the complete list of required variables.

---

## License

This project is proprietary unless otherwise specified.
