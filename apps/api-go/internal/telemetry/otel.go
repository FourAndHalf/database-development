package telemetry

import (
	"context"
	"fmt"
	"os"
	"strings"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

// parseHeaders turns "k1=v1,k2=v2" into a map for OTLP metadata (e.g. OpenObserve
// Authorization / organization / stream-name headers).
func parseHeaders(raw string) map[string]string {
	headers := map[string]string{}
	for _, pair := range strings.Split(raw, ",") {
		pair = strings.TrimSpace(pair)
		k, v, ok := strings.Cut(pair, "=")
		if !ok {
			continue
		}
		// Trim surrounding quotes so a quoted env value (e.g. via docker env_file)
		// doesn't corrupt the header, e.g. authorization="Basic ...".
		v = strings.Trim(strings.TrimSpace(v), `"`)
		headers[strings.TrimSpace(k)] = v
	}
	return headers
}

// InitTracer wires all Go API traces to OpenObserve (the API-observability
// platform). Endpoint is OPENOBSERVE_OTLP_ENDPOINT (falling back to the standard
// OTEL_EXPORTER_OTLP_ENDPOINT); if neither is set, tracing is disabled but the
// propagator is still installed so trace_ids exist and cross-service context flows.
func InitTracer(ctx context.Context) (func(context.Context) error, error) {
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))

	endpoint := os.Getenv("OPENOBSERVE_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	}
	if endpoint == "" {
		// No collector configured: no exporter, no noisy connection errors.
		return func(context.Context) error { return nil }, nil
	}

	// The OTEL ingress (Caddy -> otel-collector:4318) speaks OTLP/HTTP, not gRPC.
	// Strip the scheme; the HTTP exporter takes host:port and posts to /v1/traces.
	endpoint = strings.TrimPrefix(strings.TrimPrefix(endpoint, "https://"), "http://")

	headers := os.Getenv("OPENOBSERVE_OTLP_HEADERS")
	if headers == "" {
		headers = os.Getenv("OTEL_EXPORTER_OTLP_HEADERS")
	}

	exporter, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpoint(endpoint),
		otlptracehttp.WithInsecure(),
		otlptracehttp.WithHeaders(parseHeaders(headers)),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create OTLP trace exporter: %w", err)
	}

	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceNameKey.String("rag-go-api"),
			semconv.DeploymentEnvironmentKey.String(os.Getenv("ENVIRONMENT")),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)

	return tp.Shutdown, nil
}
