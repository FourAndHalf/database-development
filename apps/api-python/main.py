import sys
import os
import torch
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# Add the project root to the Python path to allow absolute imports from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.retrieval.query import PaperRetriever
import phoenix as px
from phoenix.otel import register
import state
from routers import query, papers

# --- Observability ---
register()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Retriever and the Local LLMs on application startup, and clean up on shutdown."""
    
    print("Loading PaperRetriever (Embedder + VectorStore)...")
    state.retriever = PaperRetriever()
    if not state.retriever.vector_store:
        print("CRITICAL: Failed to connect to VectorStore. API will not function.")
    else:
        print("PaperRetriever loaded successfully.")

    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
    )

    print("\nLoading Aether 1.0 (Qwen2.5-0.5B-Instruct)...")
    qwen_id = "Qwen/Qwen2.5-0.5B-Instruct"
    qwen_tokenizer = AutoTokenizer.from_pretrained(qwen_id)
    qwen_model = AutoModelForCausalLM.from_pretrained(
        qwen_id,
        device_map="auto"
    )
    state.llm_pipelines["aether-1.0"] = pipeline(
        "text-generation", 
        model=qwen_model, 
        tokenizer=qwen_tokenizer
    )

    print("\nLoading Aether 2.0 (Qwen2.5-1.5B-Instruct) in 4-bit precision...")
    print("This may take a minute on the first run as the model downloads.")
    
    aether2_id = "Qwen/Qwen2.5-1.5B-Instruct"
    aether2_tokenizer = AutoTokenizer.from_pretrained(aether2_id)
    aether2_model = AutoModelForCausalLM.from_pretrained(
        aether2_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    state.llm_pipelines["aether-2.0"] = pipeline(
        "text-generation", 
        model=aether2_model, 
        tokenizer=aether2_tokenizer
    )
    print("LLMs loaded successfully!\n")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    print("Shutting down resources...")
    state.retriever = None
    state.llm_pipelines = {}

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
