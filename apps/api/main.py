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
from duckduckgo_search import DDGS
import re
import phoenix as px
from phoenix.otel import register
from prometheus_fastapi_instrumentator import Instrumentator

# --- Observability ---
# Phoenix local server (optional for production, usually external)
# session = px.launch_app() 
register()

# --- Global State ---
retriever = None
llm_pipelines = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Retriever and the Local LLMs on application startup, and clean up on shutdown."""
    global retriever, llm_pipelines
    
    print("Loading PaperRetriever (Embedder + ChromaDB)...")
    retriever = PaperRetriever()
    if not retriever.collection:
        print("CRITICAL: Failed to connect to ChromaDB. API will not function.")
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
        device_map="auto" # 0.5B is small, usually fits fine without 4-bit, but can use standard settings
    )
    llm_pipelines["aether-1.0"] = pipeline(
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
    
    llm_pipelines["aether-2.0"] = pipeline(
        "text-generation", 
        model=aether2_model, 
        tokenizer=aether2_tokenizer
    )
    print("LLMs loaded successfully!\n")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    print("Shutting down resources...")
    retriever = None
    llm_pipelines = {}

# --- API Definition ---
app = FastAPI(lifespan=lifespan)

# 4. Instrument FastAPI with Prometheus
Instrumentator().instrument(app).expose(app)

# --- Pydantic Models for Request/Response ---
class QueryRequest(BaseModel):
    query: str
    n_results: int = 5
    model: str = "aether-2.0"

class Source(BaseModel):
    source_file: str
    content: str
    distance: float
    url: str | None = None

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
    if not retriever or not retriever.collection or not llm_pipelines:
        raise HTTPException(status_code=503, detail="Services are not fully initialized.")

    # Check if the user explicitly requested a web search
    use_web_search = "@web-search" in request.query
    
    # Clean the query for the vector database and web search
    clean_query = request.query.replace("@web-search", "").strip()

    print(f"\nReceived query: {request.query} | Use Web: {use_web_search}")

    # 1. Retrieve relevant documents from ChromaDB
    query_embedding = retriever.embedder.embed_text(clean_query)
    results = retriever.collection.query(
        query_embeddings=[query_embedding],
        n_results=request.n_results
    )

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    sources = [
        Source(
            source_file=meta.get('source', 'Unknown'),
            content=doc,
            distance=dist
        )
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]

    # 2. Hybrid RAG: Fetch Live Web Context via DuckDuckGo (ONLY IF REQUESTED)
    web_documents = []
    if use_web_search:
        try:
            ddgs = DDGS()
            web_results = list(ddgs.text(clean_query, max_results=2))
            for i, r in enumerate(web_results):
                web_content = f"Web Source [{r['title']}]: {r['body']}"
                web_documents.append(web_content)
                sources.append(
                    Source(
                        source_file=r['title'],
                        content=r['body'],
                        distance=0.0,
                        url=r['href']
                    )
                )
                print(f"Appended web result: {r['href']}")
        except Exception as e:
            print(f"Web search failed or rate limited: {e}")

    if not documents and not web_documents:
        return QueryResponse(answer="Could not find any relevant information in the database or the web.", sources=[])

    # 3. Construct the prompt for the LLM
    all_context_docs = documents + web_documents
    context = "\n\n---\n\n".join(all_context_docs)
    
    selected_model = request.model if request.model in llm_pipelines else "aether-2.0"
    active_pipeline = llm_pipelines[selected_model]
    
    messages = [
        {
            "role": "system", 
            "content": """You are Aether, an elite research architect specializing in distributed systems. You provide EXHAUSTIVE technical syntheses. 
DO NOT use Markdown (no **, no ##, no `). Use ONLY raw HTML (<strong>, <code>, <ul>, <li>, <table>, <h3>) and <svg>.

Your response MUST follow this structure using these EXACT XML tags:

<main>
A high-fidelity technical summary of the core concepts.
- Use <ul> and <li> for concise technical points.
- You MUST include a <svg> architecture diagram. 
  SVG RULES:
  - Use <svg viewBox="0 0 800 200" xmlns="http://www.w3.org/2000/svg">.
  - Architecture boxes: <rect x="..." y="50" width="160" height="100" rx="10" fill="rgba(139, 92, 246, 0.2)" stroke="#8b5cf6" stroke-width="2" />.
  - Text inside boxes: <text x="..." y="105" text-anchor="middle" fill="white" font-size="14" font-family="Inter, sans-serif">...</text>.
  - Connectors: <line x1="..." y1="100" x2="..." y2="100" stroke="#8b5cf6" stroke-width="2" marker-end="url(#arrowhead)" />.
</main>
<tab title="History & Evolution">
Detailed chronological account and the problems this technology solved. Use HTML lists.
</tab>
<tab title="Technical Internals">
Deep-dive into algorithms and data structures. You MUST include an HTML <table> for complexity or component comparisons.
</tab>
<tab title="Quantitative & Trade-offs">
Focus on CAP/PACELC, performance, and specific engineering trade-offs. 
</tab>

CONTENT QUALITY RULES:
1. EXHAUSTIVE: Do not give short answers. Provide deep technical insight for EVERY tag.
2. CITATION-FIRST: Reference the provided paper names directly in your text.
3. NO HALLUCINATION: If the context doesn't contain a specific detail, state that it's an architectural deduction based on general principles of the system.
4. VISUALS: Prioritize <table> and <svg> over plain text. Ensure SVGs have proper spacing so text does not overlap.
"""
        },
        {
            "role": "user", 
            "content": f"Context sources:\n{context}\n\nQuestion: {clean_query}"
        }
    ]
    
    # Format the prompt using the model's specific chat template
    prompt = active_pipeline.tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    # 4. Generate the synthesized answer
    print(f"Generating elite hyper-informative synthesis using {selected_model}...")
    outputs = active_pipeline(
        prompt, 
        max_new_tokens=2000,
        do_sample=True, 
        temperature=0.15,
        top_p=0.95
    )
    
    # Extract only the generated text
    generated_text = outputs[0]["generated_text"][len(prompt):].strip()
    
    # Parse the XML tags into a structured JSON string
    import json
    
    tabs = []
    for tab_match in re.finditer(r'<tab\s+title="([^"]+)">(.*?)</tab>', generated_text, re.DOTALL | re.IGNORECASE):
        tabs.append({"title": tab_match.group(1), "content": tab_match.group(2).strip()})
        
    main_match = re.search(r'<main>(.*?)</main>', generated_text, re.DOTALL | re.IGNORECASE)
    
    if main_match:
        main_content = main_match.group(1).strip()
        # Remove any nested tabs from the main content so they don't duplicate
        main_content = re.sub(r'<tab\s+title="[^"]+">.*?</tab>', '', main_content, flags=re.DOTALL | re.IGNORECASE).strip()
        if not main_content:
            main_content = "See tabs for details."
    else:
        # If no <main> tag, take everything that isn't a tab
        main_content = re.sub(r'<tab\s+title="[^"]+">.*?</tab>', '', generated_text, flags=re.DOTALL | re.IGNORECASE).strip()
        if not main_content:
            main_content = "See tabs for details."
        
    if main_content != "See tabs for details." or tabs:
        structured_data = {
            "main": main_content,
            "tabs": tabs
        }
    else:
        # Fallback: if the LLM ignored all tags, just wrap the whole response in the expected JSON structure
        structured_data = {
            "main": generated_text,
            "tabs": []
        }
        
    final_answer = json.dumps(structured_data)

    print("Generation complete.")
    
    return QueryResponse(answer=final_answer, sources=sources)

# --- Static File Serving ---
app.mount("/static", StaticFiles(directory="apps/ui"), name="static")

# Removed PDF static mounting, now handled by Go API Gateway

@app.delete("/api/papers/{filename}")
async def delete_paper(filename: str):
    """Deletes all chunks associated with a specific PDF filename from the vector database."""
    if not retriever or not retriever.collection:
        raise HTTPException(status_code=503, detail="Vector database not initialized.")
    
    try:
        # ChromaDB allows deleting by metadata matches
        retriever.collection.delete(where={"source": filename})
        print(f"Deleted vectors for source: {filename}")
        return {"status": "success", "deleted": filename}
    except Exception as e:
        print(f"Error deleting vectors for {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_index():
    """Serves the main index.html file."""
    return FileResponse('apps/ui/index.html')
