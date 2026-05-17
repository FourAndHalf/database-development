import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add the project root to the Python path to allow absolute imports from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.retrieval.query import PaperRetriever

# --- API Definition ---
app = FastAPI()

# --- Pydantic Models for Request/Response ---
class QueryRequest(BaseModel):
    query: str
    n_results: int = 3

class Source(BaseModel):
    source_file: str
    content: str
    distance: float

class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]

# --- Global State ---
# In a production app, you might manage this more robustly.
# For our purpose, loading the retriever once at startup is efficient.
retriever = None

@app.on_event("startup")
def startup_event():
    """Load the PaperRetriever on application startup."""
    global retriever
    print("Loading PaperRetriever...")
    retriever = PaperRetriever()
    if not retriever.collection:
        print("CRITICAL: Failed to connect to ChromaDB. API will not function.")
    print("PaperRetriever loaded successfully.")

# --- API Endpoints ---
@app.post("/api/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Handles a user's query, retrieves relevant context, and returns a
    synthesized answer with sources.
    """
    if not retriever or not retriever.collection:
        raise HTTPException(status_code=503, detail="Vector database is not available.")

    print(f"Received query: {request.query}")

    # 1. Retrieve relevant documents from ChromaDB
    query_embedding = retriever.embedder.embed_text(request.query)
    results = retriever.collection.query(
        query_embeddings=[query_embedding],
        n_results=request.n_results
    )

    # 2. Extract and format the results
    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    if not documents:
        return QueryResponse(answer="Could not find any relevant information.", sources=[])

    # 3. Synthesize the answer (Stubbed LLM)
    # In a real app, this context would be sent to an LLM like Gemini.
    # For now, we'll just join the chunks together.
    synthesized_answer = (
        "Based on the retrieved context, here is a summary:\n\n" + 
        "\n\n---\n\n".join(documents)
    )

    # 4. Format sources for the response
    sources = [
        Source(
            source_file=meta.get('source', 'Unknown'),
            content=doc,
            distance=dist
        )
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
    
    return QueryResponse(answer=synthesized_answer, sources=sources)

# --- Static File Serving ---
# Mount the 'ui' directory to serve static files (HTML, CSS, JS)
# This must come after the API routes.
app.mount("/static", StaticFiles(directory="apps/ui"), name="static")

@app.get("/")
async def read_index():
    """Serves the main index.html file."""
    return FileResponse('apps/ui/index.html')

# To run the app:
# 1. Navigate to your project root in the terminal.
# 2. Run the command: uvicorn apps.api.main:app --reload
