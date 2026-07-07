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

# Shared formatting contract: push the models toward visual, diagram-rich answers.
FORMAT_RULES = (
    "MAKE ANSWERS VISUAL AND EASY TO UNDERSTAND — favour structure and diagrams over walls of text:\n"
    "- Open with a one-sentence direct answer, then expand.\n"
    "- Use semantic HTML: <h3> headings, <p>, <strong>/<em>, <ul>/<li>, <ol>, and <table> "
    "with <thead>/<tbody> for any comparison or tradeoff. Use <code>/<pre> for code, keys, or formulas, "
    "and <blockquote> for the key takeaway.\n"
    "- Whenever a concept has structure (architecture, data flow, request/replication path, a sequence, "
    "a timeline, a tradeoff space, or a state machine), DRAW IT as an inline <svg>. Use "
    "<svg viewBox='0 0 640 360' width='100%'> with labelled <rect>/<circle> nodes, <text> labels, and "
    "<line>/<path> arrows. Keep every diagram self-contained (no external URLs, no <img>). Use clear, "
    "high-contrast colours that read on a dark UI.\n"
    "- Prefer several small, focused visuals over one dense one.\n\n"
    "OUTPUT CONTRACT — follow EXACTLY, output ONLY these tags (no markdown fences, no text outside them):\n"
    "- Wrap the primary answer in a single <main>...</main>.\n"
    "- Add zero or more <tab title=\"...\">...</tab> blocks for supplementary depth "
    "(good tab titles: 'Diagram', 'Architecture', 'Deep Dive', 'Comparison', 'Example', 'Tradeoffs')."
)

def _grounded_system(context: str) -> str:
    return (
        "You are Aether, an elite research architect specializing in distributed systems and databases. "
        "Answer the user's question grounded in the CONTEXT below. If the context is insufficient for part "
        "of the question, say so briefly rather than inventing facts.\n\n"
        f"CONTEXT:\n{context}\n\n{FORMAT_RULES}"
    )

def _followup_system() -> str:
    return (
        "You are Aether, an elite research architect. No NEW source documents were retrieved for this turn — "
        "this is a follow-up about the conversation so far (e.g. reformat it, visualize it as a diagram/table, "
        "simplify, or expand a previous answer). Fulfil it using the conversation history. Do not introduce new "
        "factual claims beyond what the conversation has already established.\n\n"
        f"{FORMAT_RULES}"
    )


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

    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    log.info("Attempting Gemini (%s)", model_name)
    client = genai.Client(api_key=api_key)

    # messages[0] is the system prompt; the rest is the multi-turn conversation
    # (history + current question). Map to Gemini's contents/roles ('assistant'->'model').
    system_instruction = messages[0]["content"]
    contents = []
    for m in messages[1:]:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    # Gemini requires the first content to be a 'user' turn.
    while contents and contents[0]["role"] == "model":
        contents.pop(0)

    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.15,
            max_output_tokens=16000,
            system_instruction=system_instruction,
        ),
    )
    return response.text


def generate_with_groq(messages, model: str):
    """Fallback generator using Groq once Gemini is exhausted/unavailable."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise Exception("GROQ_API_KEY not configured for fallback.")

    model_map = {
        "aether-1.0": "llama-3.1-8b-instant",     # Aether 1.0 (8B)
        "aether-2.0": "llama-3.3-70b-versatile",  # Aether 2.0 (70B)
    }
    groq_model = model_map.get(model, "llama-3.3-70b-versatile")

    log.info("Falling back to Groq (%s)", groq_model)
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
    completion = client.chat.completions.create(
        model=groq_model,
        messages=messages,
        temperature=0.15,
        max_tokens=16000
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

    # 4. Gate. Grounded answer if chunks/web cleared the bar. Otherwise, if there IS
    #    prior conversation, treat this as a follow-up (reformat/visualize/expand) and
    #    answer from history. Only refuse when there's nothing to work from at all.
    has_context = bool(kept_documents or web_documents)
    history = request.history or []
    if not has_context and not history:
        return QueryResponse(answer=_not_found_answer(clean_query, use_web_search), sources=[])

    # 5. Construct the multi-turn prompt: system + conversation history + current query.
    if has_context:
        context = "\n\n---\n\n".join(kept_documents + web_documents)
        system_content = _grounded_system(context)
    else:
        system_content = _followup_system()

    messages = [{"role": "system", "content": system_content}]
    for turn in history:
        role = "assistant" if turn.role == "assistant" else "user"
        messages.append({"role": role, "content": turn.text})
    messages.append({"role": "user", "content": clean_query})

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
