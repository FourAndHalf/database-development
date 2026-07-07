import sys
import os
import logging
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load .env before any project modules (telemetry/state read env vars at import time)
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from services.retrieval.query import PaperRetriever
from services.retrieval.reranker import Reranker
from apps.api_python import state
from apps.api_python.telemetry import init_telemetry
from apps.api_python.routers import query, papers

# --- Telemetry ---
# Strict split: API/infra spans -> OpenObserve (global provider); LLM spans ->
# Phoenix (dedicated provider, wired inside init_telemetry). Also installs
# trace_id log correlation. Returns the global provider for FastAPI instrumentation.
tracer_provider = init_telemetry()
log = logging.getLogger("rag-python-engine")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Retriever on application startup, and clean up on shutdown."""
    print("Loading PaperRetriever (Embedder + VectorStore)...")
    state.retriever = PaperRetriever()
    if not state.retriever.vector_store:
        print("CRITICAL: Failed to connect to VectorStore. API will not function.")
    else:
        print("PaperRetriever loaded successfully.")

    print("Loading Reranker (bge-reranker-v2-m3)...")
    state.reranker = Reranker()
    print("Reranker loaded successfully.")

    print("Inference Engine: Gemini (primary) -> Groq (fallback)")

    yield  # Application runs here

    # Cleanup on shutdown
    print("Shutting down resources...")
    state.retriever = None
    state.reranker = None

# --- API Definition ---
app = FastAPI(lifespan=lifespan)

# Instrument FastAPI with OpenTelemetry (API spans/metrics -> OpenObserve provider).
from opentelemetry import metrics
meter_provider = metrics.get_meter_provider()
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider, meter_provider=meter_provider)


@app.middleware("http")
async def trace_id_headers(request: Request, call_next):
    """
    Make every request auditable: echo the caller's X-Request-ID and surface the
    OTel trace_id as X-Trace-ID so a client or log line can be traced back to the
    exact OpenObserve/Phoenix trace.
    """
    response = await call_next(request)
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        response.headers["X-Trace-ID"] = format(ctx.trace_id, "032x")
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response

# --- Include Routers ---
app.include_router(query.router, prefix="/api")
app.include_router(papers.router, prefix="/api")

# --- Health Check ---
# This service is API-only behind Caddy; the UI is served by the Angular container.
@app.get("/health")
async def health():
    """Liveness/readiness probe used by the Docker healthcheck."""
    ready = bool(state.retriever and state.retriever.vector_store)
    return {"status": "ok", "vector_store_ready": ready}


@app.get("/")
async def read_index():
    return {"service": "rag-python-engine", "status": "ok"}
