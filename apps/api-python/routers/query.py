import re
import json
import os
from fastapi import APIRouter, HTTPException
from duckduckgo_search import DDGS
from apps.api_python.models import QueryRequest, QueryResponse, Source
from apps.api_python import state
from openai import OpenAI

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Handles a user's query, retrieves relevant context, and uses Groq API
    to synthesize a conversational answer.
    """
    if not state.retriever or not state.retriever.vector_store:
        raise HTTPException(status_code=503, detail="Services are not fully initialized.")

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    # Check if the user explicitly requested a web search
    use_web_search = "@web-search" in request.query
    
    # Clean the query for the vector database and web search
    clean_query = request.query.replace("@web-search", "").strip()

    print(f"\nReceived query: {request.query} | Use Web: {use_web_search}")

    # 1. Retrieve relevant documents from the vector store
    query_embedding = state.retriever.embedder.embed_text(clean_query)
    results = state.retriever.vector_store.query(
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
    
    # 4. Generate the synthesized answer using Groq
    print(f"Generating synthesis using Groq (Llama-3.1-70b)...")
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
        
        completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            temperature=0.15,
            max_tokens=2000
        )
        generated_text = completion.choices[0].message.content
    except Exception as e:
        print(f"Groq API call failed: {e}")
        raise HTTPException(status_code=502, detail=f"Groq API error: {str(e)}")

    tabs = []
    for tab_match in re.finditer(r'<tab\s+title="([^"]+)">(.*?)</tab>', generated_text, re.DOTALL | re.IGNORECASE):
        tabs.append({"title": tab_match.group(1), "content": tab_match.group(2).strip()})
        
    main_match = re.search(r'<main>(.*?)</main>', generated_text, re.DOTALL | re.IGNORECASE)
    
    if main_match:
        main_content = main_match.group(1).strip()
        main_content = re.sub(r'<tab\s+title="[^"]+">.*?</tab>', '', main_content, flags=re.DOTALL | re.IGNORECASE).strip()
        if not main_content:
            main_content = "See tabs for details."
    else:
        main_content = re.sub(r'<tab\s+title="[^"]+">.*?</tab>', '', generated_text, flags=re.DOTALL | re.IGNORECASE).strip()
        if not main_content:
            main_content = "See tabs for details."
        
    if main_content != "See tabs for details." or tabs:
        structured_data = {
            "main": main_content,
            "tabs": tabs
        }
    else:
        structured_data = {
            "main": generated_text,
            "tabs": []
        }
        
    final_answer = json.dumps(structured_data)

    print("Generation complete.")
    
    return QueryResponse(answer=final_answer, sources=sources)
