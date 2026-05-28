import re
import json
import os
from fastapi import APIRouter, HTTPException
from duckduckgo_search import DDGS
from apps.api_python.models import QueryRequest, QueryResponse, Source
from apps.api_python import state
from openai import OpenAI
import google.generativeai as genai

router = APIRouter()

async def generate_with_gemini(messages, model_name="gemini-1.5-flash"):
    """Fallback generator using Google Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY not configured for fallback.")
    
    print(f"Falling back to Gemini ({model_name})...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    # Convert OpenAI-style messages to Gemini format
    system_instruction = messages[0]["content"]
    user_input = messages[1]["content"]
    
    # Gemini 1.5 Flash has a slightly different chat API
    chat = model.start_chat(history=[])
    # Note: We pass the system prompt as context if the model supports it, 
    # or just prepend it to the user message for Flash 1.5.
    response = model.generate_content(
        f"System Instructions:\n{system_instruction}\n\nUser Query:\n{user_input}",
        generation_config=genai.types.GenerationConfig(
            temperature=0.15,
            max_output_tokens=2000,
        )
    )
    return response.text

@router.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Handles a user's query, retrieves relevant context, and uses Groq API
    (with Gemini fallback) to synthesize a conversational answer.
    """
    if not state.retriever or not state.retriever.vector_store:
        raise HTTPException(status_code=503, detail="Services are not fully initialized.")

    groq_api_key = os.getenv("GROQ_API_KEY")
    
    # Check if the user explicitly requested a web search
    use_web_search = "@web-search" in request.query
    clean_query = request.query.replace("@web-search", "").strip()

    # 1. Retrieve relevant documents
    query_embedding = state.retriever.embedder.embed_text(clean_query)
    results = state.retriever.vector_store.query(
        query_embeddings=[query_embedding],
        n_results=request.n_results
    )

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    sources = [
        Source(source_file=meta.get('source', 'Unknown'), content=doc, distance=dist)
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]

    # 2. Hybrid RAG (Web Context)
    web_documents = []
    if use_web_search:
        try:
            ddgs = DDGS()
            web_results = list(ddgs.text(clean_query, max_results=2))
            for r in web_results:
                web_documents.append(f"Web Source [{r['title']}]: {r['body']}")
                sources.append(Source(source_file=r['title'], content=r['body'], distance=0.0, url=r['href']))
        except Exception as e:
            print(f"Web search failed: {e}")

    if not documents and not web_documents:
        return QueryResponse(answer="Could not find any relevant information.", sources=[])

    # 3. Construct Prompt
    context = "\n\n---\n\n".join(documents + web_documents)
    messages = [
        {
            "role": "system", 
            "content": f"You are Aether, an elite research architect. Context:\n{context}\n\nRULES: Use HTML (<strong>, <code>, <ul>, <li>, <table>, <h3>) and <svg> diagrams. Follow EXACT XML structure: <main>...</main> and <tab title='...'>...</tab> tags."
        },
        {
            "role": "user", 
            "content": f"Question: {clean_query}"
        }
    ]
    
    # 4. Model Selection & Generation
    model_map = {
        "aether-1.0": "llama3-8b-8192",  # Aether 1.0 (8B)
        "aether-2.0": "llama-3.1-70b-versatile" # Aether 2.0 (70B)
    }
    groq_model = model_map.get(request.model, "llama-3.1-70b-versatile")

    generated_text = ""
    try:
        if not groq_api_key:
            raise Exception("Groq key missing, skipping to Gemini fallback.")
            
        print(f"Attempting Groq ({groq_model})...")
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
        completion = client.chat.completions.create(
            model=groq_model,
            messages=messages,
            temperature=0.15,
            max_tokens=2000
        )
        generated_text = completion.choices[0].message.content
    except Exception as e:
        print(f"Groq failed or rate limited: {e}")
        try:
            generated_text = await generate_with_gemini(messages)
        except Exception as gem_err:
            print(f"Gemini fallback also failed: {gem_err}")
            raise HTTPException(status_code=502, detail="Both Groq and Gemini services are unavailable.")

    # 5. Parse Structure
    tabs = []
    for tab_match in re.finditer(r'<tab\s+title="([^"]+)">(.*?)</tab>', generated_text, re.DOTALL | re.IGNORECASE):
        tabs.append({"title": tab_match.group(1), "content": tab_match.group(2).strip()})
        
    main_match = re.search(r'<main>(.*?)</main>', generated_text, re.DOTALL | re.IGNORECASE)
    main_content = main_match.group(1).strip() if main_match else "See tabs for details."
    
    final_answer = json.dumps({"main": main_content, "tabs": tabs})
    return QueryResponse(answer=final_answer, sources=sources)
