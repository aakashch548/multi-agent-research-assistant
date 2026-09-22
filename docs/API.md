# API Reference

Base URL: `http://localhost:8000`

## Health

### GET /
Simple health check.

**Response** `200 OK`
```json
{"status": "ok", "version": "1.0.0", "uptime": 123.45}
```

### GET /health
Detailed health check with dependency connectivity.

**Response** `200 OK`
```json
{
  "status": "ok",
  "database": "connected",
  "redis": "connected",
  "chromadb": "connected"
}
```

---

## Research

### POST /api/v1/research
Start a new research session.

**Request Body**
```json
{
  "query": "What is the impact of AI on healthcare?",
  "depth": "standard",
  "include_citations": true,
  "output_format": "markdown"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | required | The research question (3-2000 chars) |
| `depth` | enum | `standard` | `quick`, `standard`, or `deep` |
| `include_citations` | bool | `true` | Collect and verify citations |
| `output_format` | enum | `markdown` | `markdown`, `pdf`, or `both` |

**Response** `201 Created`
```json
{
  "session_id": "uuid",
  "status": "completed",
  "query": "...",
  "summary": "...",
  "report": "# Research Report\n...",
  "citations": [
    {"text": "...", "source_url": "...", "relevance_score": 0.9, "verified": true}
  ],
  "mermaid_diagram": "graph TD\n  A-->B",
  "metadata": {"duration_ms": 12345, "depth": "standard"},
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Example**
```bash
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?", "depth": "standard"}'
```

### GET /api/v1/research
List all research sessions with pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | `0` | Records to skip |
| `limit` | int | `20` | Max records (1-100) |

**Response** `200 OK`
```json
{
  "sessions": [
    {"session_id": "uuid", "query": "...", "status": "completed", "created_at": "..."}
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### GET /api/v1/research/{session_id}
Get full results for a specific session.

**Response** `200 OK` — same schema as POST response.

**Error** `404 Not Found`
```json
{"detail": "Research session 'xxx' not found."}
```

### GET /api/v1/research/{session_id}/stream
Server-Sent Events endpoint for live workflow progress.

**Response** `200 OK` (text/event-stream)
```
data: {"event_type": "agent_update", "agent_name": "PlannerAgent", "data": {...}, "timestamp": "..."}

data: {"event_type": "agent_update", "agent_name": "ResearcherAgent", "data": {...}, "timestamp": "..."}
```

### GET /api/v1/research/{session_id}/export/{format}
Download the research report.

| Parameter | Values | Description |
|-----------|--------|-------------|
| `format` | `markdown`, `pdf` | Export format |

**Response** `200 OK` — File download with appropriate Content-Type.

### DELETE /api/v1/research/{session_id}
Delete a research session and all associated data.

**Response** `204 No Content`

---

## Documents

### POST /api/v1/documents
Ingest a document into the vector store.

**Request Body**
```json
{
  "title": "My Document",
  "content": "Full text content...",
  "source_url": "https://example.com/doc",
  "metadata": {"author": "John"}
}
```

**Response** `201 Created`

### POST /api/v1/documents/search
Semantic search across stored documents.

**Request Body**
```json
{"query": "machine learning applications", "k": 5}
```

**Response** `200 OK`
```json
[
  {"document_id": "...", "content": "...", "score": 0.92, "metadata": {...}}
]
```

### GET /api/v1/documents/stats
Get vector store statistics.

**Response** `200 OK`
```json
{"total_documents": 150, "collection_name": "research_documents"}
```

---

## Error Format

All errors follow this structure:
```json
{
  "error_code": "AGENT_EXECUTION_ERROR",
  "message": "Human-readable description",
  "details": {"agent_name": "PlannerAgent"}
}
```

## Request Tracing

Every response includes an `X-Request-ID` header for correlation. Pass your own `X-Request-ID` header to use a custom correlation ID.
