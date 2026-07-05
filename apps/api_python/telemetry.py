"""
Telemetry wiring for the RAG Python engine.

Strict split across two self-hosted platforms:
  * OpenObserve <- API / infra traces (FastAPI server spans, retrieval, rerank).
    This is the *global* tracer provider.
  * Phoenix     <- LLM traces (Gemini via google-genai, Groq via the openai client),
    captured automatically by OpenInference instrumentors bound to a *dedicated*
    provider so those spans never reach OpenObserve.

Both platforms observe the same W3C trace_id: LLM spans are children of the active
FastAPI server span, so a single X-Trace-ID audit-links an OpenObserve trace to its
Phoenix view. Every log line is stamped with that trace_id too (see the filter below).

All exporters are opt-in. If an endpoint env var is unset, that exporter is skipped so
the service still runs with no collector configured.
"""
import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor

SERVICE_NAME = "rag-python-engine"
log = logging.getLogger("telemetry")


def _parse_headers(raw: str) -> dict:
    """Parse a 'k1=v1,k2=v2' string into OTLP metadata (e.g. OpenObserve auth)."""
    headers = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        headers[k.strip()] = v.strip()
    return headers


def _build_provider(endpoint: str, headers: dict) -> TracerProvider:
    """A TracerProvider that batches spans to a single OTLP/gRPC endpoint."""
    provider = TracerProvider(resource=Resource(attributes={
        "service.name": SERVICE_NAME,
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
    }))
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True, headers=headers or None)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


class _TraceContextFilter(logging.Filter):
    """Injects the active span's trace_id/span_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = "-"
            record.span_id = "-"
        return True


def _install_trace_log_correlation() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(_TraceContextFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [trace_id=%(trace_id)s span_id=%(span_id)s] %(name)s - %(message)s"
    ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def init_telemetry() -> TracerProvider:
    """
    Configure both providers and log-correlation. Returns the global (OpenObserve)
    provider so main.py can hand it to FastAPIInstrumentor.
    """
    _install_trace_log_correlation()

    # --- OpenObserve: API / infra traces (global provider) ---
    oo_endpoint = os.getenv(
        "OPENOBSERVE_OTLP_ENDPOINT", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    ).strip()
    if oo_endpoint:
        global_provider = _build_provider(oo_endpoint, _parse_headers(os.getenv("OPENOBSERVE_OTLP_HEADERS", "")))
    else:
        # No collector configured: spans are recorded (so trace_ids still exist for
        # correlation) but nothing is exported.
        global_provider = TracerProvider(resource=Resource(attributes={"service.name": SERVICE_NAME}))
    trace.set_tracer_provider(global_provider)

    # --- Phoenix: LLM traces (dedicated provider) ---
    px_endpoint = os.getenv("PHOENIX_OTLP_ENDPOINT", "").strip()
    if px_endpoint:
        phoenix_provider = _build_provider(px_endpoint, _parse_headers(os.getenv("PHOENIX_OTLP_HEADERS", "")))
        # OpenInference instrumentors emit LLM spans onto the Phoenix provider only,
        # so Gemini/Groq calls are auto-captured with prompt/model/token attributes.
        GoogleGenAIInstrumentor().instrument(tracer_provider=phoenix_provider)
        OpenAIInstrumentor().instrument(tracer_provider=phoenix_provider)

    log.info(
        "Telemetry ready | OpenObserve(API)=%s | Phoenix(LLM)=%s",
        oo_endpoint or "(disabled)", px_endpoint or "(disabled)",
    )
    return global_provider
