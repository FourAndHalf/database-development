import re
import json
import os
import logging
from contextlib import nullcontext
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from duckduckgo_search import DDGS
from opentelemetry import trace
from openinference.instrumentation import using_session
from apps.api_python.models import QueryRequest, Source
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


def _extract_grounding_sources(response) -> list[Source]:
    """Pulls Google Search grounding citations off a Gemini response, if any.

    Gemini decides on its own whether a turn needed a web search; when it does,
    candidates[0].grounding_metadata.grounding_chunks lists the pages it grounded
    on. Mapped to the same Source shape as DDG results so the frontend renders
    them identically (accordion + question breadcrumbs).
    """
    sources: list[Source] = []
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return sources
    metadata = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(metadata, "grounding_chunks", None) or []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if not web or not web.uri:
            continue
        sources.append(Source(
            source_file=web.title or web.uri,
            content=web.title or "",
            distance=0.0,
            url=web.uri,
        ))
    return sources


async def generate_with_gemini_stream(messages, sources_out: list, model_name=None):
    """Primary generator using Google Gemini (free tier) via the google-genai SDK.

    Yields text deltas as they arrive. Grounding citations (if the model used
    Google Search) are appended to `sources_out` in place, since an async
    generator can't both yield chunks and return a value.

    OpenInference auto-instruments this client, so the call is captured as an LLM
    span (prompt/model/tokens) on the Phoenix provider. Google Search grounding is
    enabled so Gemini can cite external pages for a query even when the user didn't
    opt into @web-search; grounding is model-decided and returns no chunks when it
    isn't used.
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

    stream = await client.aio.models.generate_content_stream(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.15,
            max_output_tokens=16000,
            system_instruction=system_instruction,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    async for chunk in stream:
        grounded = _extract_grounding_sources(chunk)
        if grounded:
            sources_out[:] = grounded
        if chunk.text:
            yield chunk.text


def generate_with_groq_stream(messages, model: str):
    """Fallback generator using Groq once Gemini is exhausted/unavailable. Yields text deltas."""
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
    stream = client.chat.completions.create(
        model=groq_model,
        messages=messages,
        temperature=0.15,
        max_tokens=16000,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content if event.choices else None
        if delta:
            yield delta


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_answer(messages, model: str, sources: list):
    """Streams raw text chunks from Gemini, falling back to Groq on failure.

    Fallback is only safe BEFORE any chunk has reached the client — once Gemini's
    stream has emitted output, switching providers mid-answer would produce a
    jarring, disjointed response, so a failure at that point just truncates the
    answer with a short notice instead of silently swapping generators.

    Yields ("token", text) for each chunk and, at most once, ("error", detail) if
    both providers fail before any output was produced.
    """
    emitted_any = False
    gemini_sources: list = []
    try:
        async for chunk in generate_with_gemini_stream(messages, gemini_sources):
            emitted_any = True
            yield ("token", chunk)
        seen_urls = {s.url for s in sources if s.url}
        sources.extend(s for s in gemini_sources if s.url not in seen_urls)
    except Exception as e:
        log.warning("Gemini failed or rate limited: %s", e)
        if emitted_any:
            log.error("Gemini failed mid-stream after partial output; not falling back to Groq.")
            yield ("token", "\n\n<em>[Response was cut short due to a generation error.]</em>")
        else:
            try:
                for chunk in generate_with_groq_stream(messages, model):
                    yield ("token", chunk)
            except Exception as groq_err:
                log.error("Groq fallback also failed: %s", groq_err)
                yield ("error", "Both Gemini and Groq services are unavailable.")


@router.post("/query")
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
        async def not_found_stream():
            payload = json.loads(_not_found_answer(clean_query, use_web_search))
            yield _sse("token", payload["main"])
            yield _sse("final", {"main": payload["main"], "tabs": [], "sources": []})
        return StreamingResponse(not_found_stream(), media_type="text/event-stream")

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

    # 6. Generation: Gemini primary -> Groq fallback (only before the first token is
    #    sent; see _stream_answer). Tag both LLM calls with the conversation id as a
    #    Phoenix session, so every turn of a conversation groups together in the
    #    Phoenix Sessions view instead of appearing as unrelated traces.
    async def event_stream():
        buffer = []
        session_ctx = using_session(request.conversation_id) if request.conversation_id else nullcontext()
        with session_ctx:
            async for kind, payload in _stream_answer(messages, request.model, sources):
                if kind == "token":
                    buffer.append(payload)
                    yield _sse("token", payload)
                elif kind == "error":
                    yield _sse("error", {"detail": payload})

        generated_text = "".join(buffer)
        if not generated_text:
            return  # both providers failed before any output; client already got an error event

        # 7. Parse Structure — same regex contract as before, applied to the full text
        #    now that streaming has finished.
        tabs = []
        for tab_match in re.finditer(r'<tab\s+title="([^"]+)">(.*?)</tab>', generated_text, re.DOTALL | re.IGNORECASE):
            tabs.append({"title": tab_match.group(1), "content": tab_match.group(2).strip()})

        main_match = re.search(r'<main>(.*?)</main>', generated_text, re.DOTALL | re.IGNORECASE)
        # The model doesn't always follow the <main> output contract (more likely on long
        # follow-up turns) — fall back to the raw text rather than discarding the answer.
        main_content = main_match.group(1).strip() if main_match else generated_text.strip()

        yield _sse("final", {
            "main": main_content,
            "tabs": tabs,
            "sources": [s.model_dump() for s in sources],
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
