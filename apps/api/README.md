# API (Go) — Mock RAG Chat Backend

Minimal HTTP API used by `apps/ui` during RAG development. The `/v1/chat` endpoint is mocked today (no real retrieval yet), but the types and seams are in place to plug in your retriever/reranker/LLM orchestration.

## Run

```bash
cd apps/api
go run ./cmd/api
```

Env vars:
- `PORT` (default `8080`)
- `UI_ORIGIN` (default `http://localhost:4200`) used for CORS

## Endpoints

- `GET /healthz`
- `POST /v1/chat`

