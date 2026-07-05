package middleware

import (
	"context"
	"net/http"

	"database-development/apps/api-go/internal/util"
	"go.opentelemetry.io/otel/trace"
)

type ctxKey string

const requestIDKey ctxKey = "request_id"

// RequestID makes every request auditable. It assigns (or honors an inbound)
// X-Request-ID, stashes it in the context so downstream calls can forward it,
// and echoes both the request id and the OTel trace id back on the response so a
// client or log line can be traced straight to the OpenObserve/Phoenix trace.
//
// Must sit inside the otelhttp handler (it reads the server span) and before
// RequestLog (which logs the ids).
func RequestID() Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			rid := r.Header.Get("X-Request-ID")
			if rid == "" {
				rid = util.NewID()
			}
			ctx := context.WithValue(r.Context(), requestIDKey, rid)

			w.Header().Set("X-Request-ID", rid)
			if sc := trace.SpanFromContext(ctx).SpanContext(); sc.HasTraceID() {
				w.Header().Set("X-Trace-ID", sc.TraceID().String())
			}
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// RequestIDFromContext returns the request id assigned by the RequestID middleware,
// or "" if none is present.
func RequestIDFromContext(ctx context.Context) string {
	rid, _ := ctx.Value(requestIDKey).(string)
	return rid
}

// TraceIDFromContext returns the current span's trace id as a hex string, or "-".
func TraceIDFromContext(ctx context.Context) string {
	if sc := trace.SpanFromContext(ctx).SpanContext(); sc.HasTraceID() {
		return sc.TraceID().String()
	}
	return "-"
}
