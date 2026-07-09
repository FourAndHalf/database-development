# API (Go) — Mock RAG Chat Backend

Minimal HTTP API used by `apps/ui` during RAG development. The `/v1/chat` endpoint is mocked today (no real retrieval yet), but the types and seams are in place to plug in your retriever/reranker/LLM orchestration.

## Run

```bash
cd apps/api-go
go run ./cmd/api
```

Env vars:
- `PORT` (default `8081`)
- `UI_ORIGIN` (default `http://localhost:4200`) used for CORS
- `RAG_ENGINE` (default `python`) set to `python` to call the Python retrieval service
- `PYTHON_SERVICE_URL` (default `http://localhost:8000`) used when `RAG_ENGINE=python`

## Endpoints

- `GET /healthz`
- `POST /v1/chat`
