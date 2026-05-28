import sys
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# Add the project root to the Python path to allow absolute imports from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.retrieval.query import PaperRetriever
import phoenix as px
from phoenix.otel import register
from apps.api_python import state
from apps.api_python.routers import query, papers

# --- Observability ---
register()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Retriever on application startup, and clean up on shutdown."""
    
    print("Loading PaperRetriever (Embedder + VectorStore)...")
    state.retriever = PaperRetriever()
    if not state.retriever.vector_store:
        print("CRITICAL: Failed to connect to VectorStore. API will not function.")
    else:
        print("PaperRetriever loaded successfully.")

    print("Inference Engine: Groq API (External)")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    print("Shutting down resources...")
    state.retriever = None

# --- API Definition ---
app = FastAPI(lifespan=lifespan)

# Instrument FastAPI with Prometheus
Instrumentator().instrument(app).expose(app)

# --- Include Routers ---
app.include_router(query.router, prefix="/api")
app.include_router(papers.router, prefix="/api")

# --- Static File Serving ---
app.mount("/static", StaticFiles(directory="apps/ui"), name="static")

@app.get("/")
async def read_index():
    """Serves the main index.html file."""
    return FileResponse('apps/ui/index.html')
