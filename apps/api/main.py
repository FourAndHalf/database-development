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

    print("\nLoading Local LLM (Llama-3.2-3B-Instruct) in 4-bit precision...")
    print("This may take a minute on the first run as the model downloads.")
    
    model_id = "unsloth/Llama-3.2-3B-Instruct"
    device = 0 if torch.cuda.is_available() else -1
    
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    llm_pipeline = pipeline(
        "text-generation", 
        model=model, 
        tokenizer=tokenizer
    )
    print("LLM loaded successfully!\n")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    print("Shutting down resources...")
    retriever = None
    llm_pipeline = None

# --- API Definition ---
app = FastAPI(lifespan=lifespan)

# 4. Instrument FastAPI with Prometheus
Instrumentator().instrument(app).expose(app)

# --- Pydantic Models for Request/Response ---
class QueryRequest(BaseModel):
    query: str
    n_results: int = 3

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
    if not retriever or not retriever.collection or not llm_pipeline:
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
    
    messages = [
        {
            "role": "system", 
            "content": """You are Aether, an elite research architect specializing in distributed systems and databases. You are chained with OpenUI capabilities to generate stunning, interactive UI components and data visualizations.
Your goal is to provide EXHAUSTIVE, multi-layered research syntheses. DO NOT output plain walls of text. You MUST prioritize bullet points, HTML tables, and OpenUI-style SVG graphs.

You MUST structure your response using these EXACT XML tags. Do NOT use JSON.

<main>
A high-fidelity technical deep-dive. 
- Use <ul> and <li> for perfectly articulated, concise bullet points.
- Use BEAUTIFUL COLORFUL SVG diagrams to illustrate architectures.
- Use OpenUI-styled SVG bar charts, line graphs, or scatter plots to provide deep insights into quantitative measures (e.g., latency, throughput, scale). Ensure these graphs are visually stunning and clearly labeled.
- Use <table> for comparisons.
</main>
<tab title="History & Evolution">
Chronological account (citing papers), evolution, and problems solved. Use HTML bullet points and timelines.
</tab>
<tab title="Technical Internals">
Deep technical analysis. MUST include at least one <table> or <svg> diagram showing data structures, algorithmic complexity, or architecture.
</tab>
<tab title="Quantitative & Trade-offs">
Focus on CAP theorem, PACELC, performance metrics. USE OpenUI-styled SVG CHARTS to show quantitative measures. Use <table> for trade-offs.
</tab>

VISUAL & CONTENT RULES:
- NEVER use Markdown (no **, no ##, no `). ONLY use raw HTML (e.g., <strong>, <code>, <ul>, <li>, <h3>) and <svg>.
- For SVGs, use vibrant gradients, clean lines, text labels, proper <viewBox>, and make them visually stunning (emulating OpenUI component generation).
- Prioritize bullet points, HTML tables, and SVGs over large blocks of plain text.
- Be academically rigorous. Reference the provided paper contexts by name where possible.
- If context is missing for a specific tab, use the available information to provide the best possible historical or technical deduction.

Your synthesis should feel like a premium, published research briefing."""
        },
        {
            "role": "user", 
            "content": f"Context sources:\n{context}\n\nQuestion: {clean_query}"
        }
    ]
    
    # Format the prompt using Qwen's specific chat template
    prompt = llm_pipeline.tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    # 4. Generate the synthesized answer
    print("Generating elite hyper-informative synthesis...")
    outputs = llm_pipeline(
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

# Mount PDF directory for viewing
pdf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/raw_pdfs'))
if os.path.exists(pdf_dir):
    app.mount("/pdfs", StaticFiles(directory=pdf_dir), name="pdfs")

@app.get("/")
async def read_index():
    """Serves the main index.html file."""
    return FileResponse('apps/ui/index.html')
