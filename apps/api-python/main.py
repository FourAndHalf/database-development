import sys
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.resources import RESOURCE_ATTRIBUTES, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.retrieval.query import PaperRetriever
from services.retrieval.reranker import Reranker
from apps.api_python import state
from apps.api_python.routers import query, papers

# --- OpenTelemetry Configuration ---
# Empty/unset disables trace export (avoids exporter errors when no collector is configured).
OTEL_COLLECTOR_URL = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
resource = Resource(attributes={
    "service.name": "rag-python-engine",
    "environment": os.getenv("ENVIRONMENT", "production")
})

provider = TracerProvider(resource=resource)
if OTEL_COLLECTOR_URL:
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_COLLECTOR_URL, insecure=True))
    provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

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

    print(f"Observability: Exporting traces to {OTEL_COLLECTOR_URL or '(disabled)'}")
    print("Inference Engine: Gemini (primary) -> Groq (fallback)")

    yield  # Application runs here

    # Cleanup on shutdown
    print("Shutting down resources...")
    state.retriever = None
    state.reranker = None

# --- API Definition ---
app = FastAPI(lifespan=lifespan)

# Instrument FastAPI with Prometheus
Instrumentator().instrument(app).expose(app)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

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
