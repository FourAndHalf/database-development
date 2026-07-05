import re
import json
import os
import logging
from fastapi import APIRouter, HTTPException
from duckduckgo_search import DDGS
from opentelemetry import trace
from apps.api_python.models import QueryRequest, QueryResponse, Source
from apps.api_python import state
from openai import OpenAI
from google import genai
from google.genai import types

router = APIRouter()
log = logging.getLogger("rag.query")
# Infra spans (retrieve/rerank/web) go to the global provider -> OpenObserve.
tracer = trace.get_tracer("rag.query")

# Only rerank scores at/above this (sigmoid 0-1) are trusted enough to answer from.
RERANK_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "0.5"))
# Broad first-stage pool handed to the cross-encoder before it narrows to n_results.
CANDIDATE_POOL = int(os.getenv("RETRIEVAL_CANDIDATE_POOL", "20"))


def _not_found_answer(query: str, web_searched: bool) -> str:
    """Builds a personalized 'no relevant data' message instead of hallucinating."""
    msg = (
        f"<main>I couldn't find anything relevant to <strong>\"{query}\"</strong> "
        f"in the knowledge base.</main>"
    )
    if not web_searched:
        msg += (
            "<main>This corpus focuses on distributed systems and database papers. "
            "Try rephrasing, or add <code>@web-search</code> to your question so I can "
            "look it up on the web.</main>"
        )
    else:
        msg += "<main>The web search didn't surface anything useful either. Try rephrasing your question.</main>"
    return json.dumps({"main": msg, "tabs": []})


async def generate_with_gemini(messages, model_name=None):
    """Primary generator using Google Gemini (free tier) via the google-genai SDK.

    OpenInference auto-instruments this client, so the call is captured as an LLM
    span (prompt/model/tokens) on the Phoenix provider.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY not configured.")

    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    log.info("Attempting Gemini (%s)", model_name)
    client = genai.Client(api_key=api_key)

    # Convert OpenAI-style messages to a single Gemini prompt.
    system_instruction = messages[0]["content"]
    user_input = messages[1]["content"]

    response = client.models.generate_content(
        model=model_name,
        contents=f"System Instructions:\n{system_instruction}\n\nUser Query:\n{user_input}",
        config=types.GenerateContentConfig(
            temperature=0.15,
            max_output_tokens=2000,
        ),
    )
    return response.text


def generate_with_groq(messages, model: str):
    """Fallback generator using Groq once Gemini is exhausted/unavailable."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise Exception("GROQ_API_KEY not configured for fallback.")

    model_map = {
        "aether-1.0": "llama3-8b-8192",          # Aether 1.0 (8B)
        "aether-2.0": "llama-3.1-70b-versatile",  # Aether 2.0 (70B)
    }
    groq_model = model_map.get(model, "llama-3.1-70b-versatile")

    log.info("Falling back to Groq (%s)", groq_model)
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
    completion = client.chat.completions.create(
        model=groq_model,
        messages=messages,
        temperature=0.15,
        max_tokens=2000
    )
    return completion.choices[0].message.content


@router.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Handles a user's query: retrieve -> rerank -> threshold-gate -> synthesize.
    Inference uses Gemini (primary) with Groq fallback. Web search is opt-in via
    the @web-search decorator.
    """
    if not state.retriever or not state.retriever.vector_store or not state.reranker:
        raise HTTPException(status_code=503, detail="Services are not fully initialized.")

    # Check if the user explicitly requested a web search
    use_web_search = "@web-search" in request.query
    clean_query = request.query.replace("@web-search", "").strip()

    # 1. Retrieve a broad candidate pool from the vector store.
    with tracer.start_as_current_span("rag.retrieve") as span:
        span.set_attribute("rag.web_search", use_web_search)
        span.set_attribute("rag.candidate_pool", CANDIDATE_POOL)
        query_embedding = state.retriever.embedder.embed_text(clean_query)
        results = state.retriever.vector_store.query(
            query_embeddings=[query_embedding],
            n_results=CANDIDATE_POOL
        )
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        span.set_attribute("rag.candidates_returned", len(documents))

    # 2. Rerank with the cross-encoder and keep only chunks above threshold.
    sources = []
    kept_documents = []
    with tracer.start_as_current_span("rag.rerank") as span:
        span.set_attribute("rag.rerank_threshold", RERANK_THRESHOLD)
        span.set_attribute("rag.top_k", request.n_results)
        if documents:
            ranked = state.reranker.rerank(clean_query, documents, top_k=request.n_results)
            span.set_attribute("rag.top_score", ranked[0]["score"] if ranked else 0.0)
            for r in ranked:
                if r["score"] < RERANK_THRESHOLD:
                    continue
                i = r["index"]
                kept_documents.append(documents[i])
                sources.append(Source(
                    source_file=metadatas[i].get('source', 'Unknown'),
                    content=documents[i],
                    distance=distances[i],
                ))
        span.set_attribute("rag.chunks_kept", len(kept_documents))

    # 3. Optional web context (explicit user request bypasses the threshold gate).
    web_documents = []
    if use_web_search:
        with tracer.start_as_current_span("rag.web_search") as span:
            try:
                ddgs = DDGS()
                web_results = list(ddgs.text(clean_query, max_results=2))
                for r in web_results:
                    web_documents.append(f"Web Source [{r['title']}]: {r['body']}")
                    sources.append(Source(source_file=r['title'], content=r['body'], distance=0.0, url=r['href']))
                span.set_attribute("rag.web_results", len(web_documents))
            except Exception as e:
                span.record_exception(e)
                log.warning("Web search failed: %s", e)

    # 4. Nothing relevant cleared the bar -> personalized not-found, no hallucinating.
    if not kept_documents and not web_documents:
        return QueryResponse(answer=_not_found_answer(clean_query, use_web_search), sources=[])

    # 5. Construct Prompt
    context = "\n\n---\n\n".join(kept_documents + web_documents)
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

    # 6. Generation: Gemini primary -> Groq fallback.
    try:
        generated_text = await generate_with_gemini(messages)
    except Exception as e:
        log.warning("Gemini failed or rate limited: %s", e)
        try:
            generated_text = generate_with_groq(messages, request.model)
        except Exception as groq_err:
            log.error("Groq fallback also failed: %s", groq_err)
            raise HTTPException(status_code=502, detail="Both Gemini and Groq services are unavailable.")

    # 7. Parse Structure
    tabs = []
    for tab_match in re.finditer(r'<tab\s+title="([^"]+)">(.*?)</tab>', generated_text, re.DOTALL | re.IGNORECASE):
        tabs.append({"title": tab_match.group(1), "content": tab_match.group(2).strip()})

    main_match = re.search(r'<main>(.*?)</main>', generated_text, re.DOTALL | re.IGNORECASE)
    main_content = main_match.group(1).strip() if main_match else "See tabs for details."

    final_answer = json.dumps({"main": main_content, "tabs": tabs})
    return QueryResponse(answer=final_answer, sources=sources)
