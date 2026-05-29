import sys
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
from apps.api_python import state
from apps.api_python.routers import query, papers

# --- OpenTelemetry Configuration ---
OTEL_COLLECTOR_URL = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel.observability.duckdns.org:4317")
resource = Resource(attributes={
    "service.name": "rag-python-engine",
    "environment": os.getenv("ENVIRONMENT", "production")
})

provider = TracerProvider(resource=resource)
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

    print(f"Observability: Exporting traces to {OTEL_COLLECTOR_URL}")
    print("Inference Engine: Groq API (External)")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    print("Shutting down resources...")
    state.retriever = None

# --- API Definition ---
app = FastAPI(lifespan=lifespan)

# Instrument FastAPI with Prometheus
Instrumentator().instrument(app).expose(app)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# --- Include Routers ---
app.include_router(query.router, prefix="/api")
app.include_router(papers.router, prefix="/api")

# --- Static File Serving ---
app.mount("/static", StaticFiles(directory="apps/ui"), name="static")

@app.get("/")
async def read_index():
    """Serves the main index.html file."""
    # Assuming static files are correctly mapped in the final deployment
    return FileResponse('apps/ui/index.html')
