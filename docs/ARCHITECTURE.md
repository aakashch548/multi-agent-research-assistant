# Architecture

## System Overview

The Multi-Agent Research Assistant is built on a layered architecture with clear separation of concerns between the API layer, service layer, workflow orchestration, and data access.

```
                    ┌─────────────────────────┐
                    │   Streamlit Frontend     │
                    └────────────┬────────────┘
                                 │ HTTP / SSE
                    ┌────────────▼────────────┐
                    │   FastAPI + Middleware    │
                    │   (Routes, CORS, Auth)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Service Layer          │
                    │ ResearchService           │
                    │ DocumentService           │
                    └──────┬──────────┬───────┘
                           │          │
              ┌────────────▼──┐  ┌────▼──────────┐
              │  LangGraph     │  │ RAG Pipeline   │
              │  Workflow      │  │ Chunker        │
              │  ┌──────────┐  │  │ Embeddings     │
              │  │ Planner  │  │  │ VectorStore    │
              │  │ Research │  │  │ Retriever      │
              │  │ Verifier │  │  └────┬───────────┘
              │  │ Summary  │  │       │
              │  │ Writer   │  │       │
              │  └──────────┘  │       │
              └────────┬───────┘       │
                       │               │
           ┌───────────▼───┐ ┌─────────▼────┐ ┌───────┐
           │  PostgreSQL   │ │   ChromaDB    │ │ Redis │
           │  (Sessions)   │ │   (Vectors)   │ │(Cache)│
           └───────────────┘ └──────────────┘ └───────┘
```

## Agent Pipeline

Each agent is a self-contained unit that receives the shared `ResearchState` and returns a partial update:

| Agent | Input | Output | Purpose |
|-------|-------|--------|---------|
| **PlannerAgent** | `query` | `plan` (list of sub-questions) | Decompose complex queries into researchable atoms |
| **ResearcherAgent** | `plan` | `research_results`, `citations` | Execute web search + RAG retrieval per sub-question |
| **VerifierAgent** | `research_results` | `verified_facts` | Cross-reference, score confidence, flag contradictions |
| **SummarizerAgent** | `verified_facts` | `summary` | Produce executive summary with key findings |
| **WriterAgent** | `summary`, `verified_facts`, `citations` | `report`, `mermaid_diagram` | Generate structured markdown report |

## LangGraph Workflow

The workflow is a compiled `StateGraph` with conditional edges:

```
START → Planner
         │
         ├─ error + retries left → Researcher (graceful degradation)
         ├─ empty plan → END
         └─ ok → Researcher
                   │
                   ├─ error + retries left → Researcher (retry)
                   ├─ no results → END
                   └─ ok → Verifier
                             │
                             ├─ low confidence + retries → Researcher (re-research)
                             └─ ok → Summarizer → Writer → END
```

Retry logic uses `retry_count` and `max_retries` fields in the shared state.

## Data Flow

1. **Request** → FastAPI validates via Pydantic schema
2. **Service** → Creates database session record, launches workflow
3. **Planner** → LLM decomposes query into 3-7 sub-questions
4. **Researcher** → For each sub-question: Tavily search → RAG retrieval → LLM synthesis
5. **Verifier** → LLM cross-references all findings for accuracy
6. **Summarizer** → LLM produces executive summary
7. **Writer** → LLM generates full report + Mermaid diagram
8. **Service** → Persists results, returns response

## Technology Rationale

| Technology | Why |
|-----------|-----|
| **FastAPI** | Async-native, automatic OpenAPI docs, Pydantic integration |
| **LangGraph** | First-class stateful agent orchestration with conditional routing |
| **LangChain** | Unified LLM interface, prompt templates, output parsing |
| **PostgreSQL** | Reliable relational storage for session persistence |
| **ChromaDB** | Purpose-built vector database for RAG retrieval |
| **Redis** | Session caching and pub/sub for real-time streaming |
| **Streamlit** | Rapid frontend development with built-in data visualization |
| **structlog** | Structured JSON logging with correlation ID propagation |
| **Pydantic v2** | High-performance data validation at API boundaries |
| **tenacity** | Robust retry logic for external service calls |

## Design Patterns

- **Repository Pattern** — Data access isolated behind `SessionRepository` and `StepRepository`
- **Service Layer** — Business logic in `ResearchService` decoupled from HTTP concerns
- **Dependency Injection** — FastAPI's `Depends()` for testable, loosely-coupled components
- **Abstract Base Class** — `BaseAgent` provides unified logging, timing, error handling
- **Factory Pattern** — `create_app()` for configurable FastAPI application construction
- **State Machine** — LangGraph `StateGraph` with conditional transitions
