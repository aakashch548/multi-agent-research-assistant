# Multi-Agent Research Assistant

A production-grade autonomous AI research system where specialized agents collaborate to answer complex research questions. Built with FastAPI, LangGraph, LangChain, PostgreSQL, ChromaDB, and Redis.

## Features

- **Multi-Agent Orchestration** — LangGraph-powered workflow with 5 specialized agents
- **Planner Agent** — Decomposes complex queries into atomic researchable sub-questions
- **Researcher Agent** — Executes web search via Tavily + RAG retrieval from ChromaDB
- **Verifier Agent** — Cross-references findings, scores confidence, flags contradictions
- **Summarizer Agent** — Produces concise summaries with confidence assessments
- **Writer Agent** — Generates structured markdown reports with inline citations
- **RAG Pipeline** — Document chunking, embeddings, vector storage, semantic retrieval
- **Citation Generation** — APA formatting, inline references, verified sources
- **Export** — Markdown and PDF report download
- **Mermaid Diagrams** — Auto-generated concept maps and workflow visualizations
- **Session Memory** — Full persistence of research sessions with PostgreSQL
- **Streaming** — Real-time SSE progress updates during workflow execution
- **REST API** — Comprehensive FastAPI endpoints with OpenAPI documentation
- **Modern Frontend** — Streamlit UI with live workflow visualization
- **Dockerized** — Full Docker Compose deployment with all dependencies

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                      │
│         Query Input | Workflow Viz | Report Display        │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼───────────────────────────────────┐
│                   FastAPI Backend                          │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Research    │  │  Document    │  │  Health          │   │
│  │ Routes     │  │  Routes      │  │  Routes          │   │
│  └─────┬──────┘  └──────┬───────┘  └─────────────────┘   │
│        │                │                                  │
│  ┌─────▼────────────────▼──────────────────────────────┐  │
│  │              Service Layer                           │  │
│  │  ResearchService    DocumentService                  │  │
│  └─────┬────────────────────────────────────────────┬──┘  │
│        │                                            │     │
│  ┌─────▼──────────────────┐  ┌──────────────────────▼──┐  │
│  │  LangGraph Workflow     │  │    RAG Pipeline          │  │
│  │  ┌───────┐ ┌─────────┐ │  │  Chunker → Embeddings    │  │
│  │  │Planner│→│Researcher│ │  │  → VectorStore           │  │
│  │  └───────┘ └────┬────┘ │  │  → Retriever              │  │
│  │           ┌─────▼────┐ │  └──────────────┬────────────┘  │
│  │           │ Verifier  │ │                │               │
│  │           └─────┬────┘ │                │               │
│  │           ┌─────▼────┐ │                │               │
│  │           │Summarizer│ │                │               │
│  │           └─────┬────┘ │                │               │
│  │           ┌─────▼────┐ │                │               │
│  │           │  Writer   │ │                │               │
│  │           └──────────┘ │                │               │
│  └────────────────────────┘                │               │
│                                            │               │
│  ┌─────────────────┐ ┌──────────┐ ┌────────▼────────┐     │
│  │   PostgreSQL     │ │  Redis   │ │   ChromaDB       │     │
│  │   (Sessions)     │ │  (Cache) │ │   (Vectors)      │     │
│  └─────────────────┘ └──────────┘ └─────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- OpenAI API key
- Tavily API key

## Quick Start

### Using Docker (recommended)

```bash
# Clone and navigate to the project
cd Project

# Copy and edit environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Start all services
docker-compose up -d

# Open the application
# Frontend: http://localhost:8501
# API docs: http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Start infrastructure (PostgreSQL, Redis, ChromaDB)
docker-compose up -d postgres redis chroma

# Run the backend
make dev

# In a separate terminal, run the frontend
make frontend
```

## API Documentation

Interactive API docs are available at `http://localhost:8000/docs` when running in development mode.

See [docs/API.md](docs/API.md) for the full endpoint reference.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model to use |
| `TAVILY_API_KEY` | — | Tavily search API key (required) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8000` | ChromaDB port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Runtime environment |
| `CHUNK_SIZE` | `1000` | Document chunk size for RAG |
| `CHUNK_OVERLAP` | `200` | Chunk overlap for RAG |

## Project Structure

```
Project/
├── backend/
│   ├── agents/          # AI agent implementations
│   ├── api/             # FastAPI routes and middleware
│   ├── core/            # Config, logging, exceptions, DI
│   ├── models/          # SQLAlchemy ORM + LangGraph state
│   ├── rag/             # RAG pipeline (chunking, embeddings, retrieval)
│   ├── repositories/    # Data access layer (repository pattern)
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic orchestration
│   ├── tools/           # Search, citations, export, diagrams
│   ├── utils/           # Helper utilities
│   ├── workflows/       # LangGraph workflow definitions
│   └── tests/           # Unit and integration tests
├── frontend/            # Streamlit UI
├── docker/              # Dockerfiles
├── docs/                # Architecture and API documentation
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

## Interview preparation

Technical interview questions and model answers for this project:

- [docs/Multi-Agent-Research-Assistant-Interview-Questions.pdf](docs/Multi-Agent-Research-Assistant-Interview-Questions.pdf)

Regenerate after edits:

```bash
pip install fpdf2
python scripts/generate_interview_pdf.py
```

## Testing

```bash
# Run all tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration
```

## License

MIT
