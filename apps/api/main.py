import sys
import os
import torch
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# Add the project root to the Python path to allow absolute imports from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.retrieval.query import PaperRetriever

from contextlib import asynccontextmanager

# --- Global State ---
retriever = None
llm_pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Retriever and the Local LLM on application startup, and clean up on shutdown."""
    global retriever, llm_pipeline
    
    print("Loading PaperRetriever (Embedder + ChromaDB)...")
    retriever = PaperRetriever()
    if not retriever.collection:
        print("CRITICAL: Failed to connect to ChromaDB. API will not function.")
    else:
        print("PaperRetriever loaded successfully.")

    print("\nLoading Local LLM (Qwen2.5-0.5B-Instruct)...")
    print("This may take a minute on the first run as the model downloads.")
    
    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    device = 0 if torch.cuda.is_available() else -1
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id)
    
    llm_pipeline = pipeline(
        "text-generation", 
        model=model, 
        tokenizer=tokenizer, 
        device=device
    )
    print("LLM loaded successfully!\n")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    print("Shutting down resources...")
    retriever = None
    llm_pipeline = None

# --- API Definition ---
app = FastAPI(lifespan=lifespan)

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

# --- API Endpoints ---
@app.post("/api/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Handles a user's query, retrieves relevant context, and uses a local LLM
    to synthesize a conversational answer.
    """
    if not retriever or not retriever.collection or not llm_pipeline:
        raise HTTPException(status_code=503, detail="Services are not fully initialized.")

    print(f"\nReceived query: {request.query}")

    # 1. Retrieve relevant documents from ChromaDB
    query_embedding = retriever.embedder.embed_text(request.query)
    results = retriever.collection.query(
        query_embeddings=[query_embedding],
        n_results=request.n_results
    )

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    if not documents:
        return QueryResponse(answer="Could not find any relevant information in the database.", sources=[])

    # 2. Construct the prompt for the LLM
    context = "\n\n---\n\n".join(documents)
    
    messages = [
        {
            "role": "system", 
            "content": "You are a helpful research assistant specializing in databases. Answer the user's question using ONLY the provided context. If the answer is not contained in the context, say 'I don't know based on the provided papers.' You MUST format your response using beautifully styled HTML. Never use Markdown. Always use raw HTML tags (like <p>, <ul>, <li>, <strong>). For comparisons or structured data, always use an HTML <table>. Be concise and informative."
        },
        {
            "role": "user", 
            "content": f"Context documents:\n{context}\n\nQuestion: {request.query}"
        }
    ]
    
    # Format the prompt using Qwen's specific chat template
    prompt = llm_pipeline.tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    # 3. Generate the synthesized answer
    print("Generating answer with LLM...")
    outputs = llm_pipeline(
        prompt, 
        max_new_tokens=300, 
        do_sample=True, 
        temperature=0.3, # Low temperature for factual consistency
        top_p=0.9
    )
    
    # Extract only the generated text (remove the prompt from the output)
    generated_text = outputs[0]["generated_text"][len(prompt):]
    print("Generation complete.")

    # 4. Format sources for the response
    sources = [
        Source(
            source_file=meta.get('source', 'Unknown'),
            content=doc,
            distance=dist
        )
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
    
    return QueryResponse(answer=generated_text.strip(), sources=sources)

# --- Static File Serving ---
app.mount("/static", StaticFiles(directory="apps/ui"), name="static")

@app.get("/")
async def read_index():
    """Serves the main index.html file."""
    return FileResponse('apps/ui/index.html')
