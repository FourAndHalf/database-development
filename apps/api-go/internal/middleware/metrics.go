package middleware

import (
	"fmt"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	httpDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "http_duration_seconds",
		Help: "Duration of HTTP requests.",
	}, []string{"path", "method", "status"})
)

func Prometheus() Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			ww := &statusWriter{ResponseWriter: w, status: http.StatusOK}
			next.ServeHTTP(ww, r)
			duration := time.Since(start).Seconds()
			// Label on the matched route pattern (e.g. "GET /v1/papers/{id}"), not the
			// raw path, so IDs don't explode metric cardinality. Falls back to
			// "unmatched" for paths with no registered handler.
			route := r.Pattern
			if route == "" {
				route = "unmatched"
			}
			httpDuration.WithLabelValues(route, r.Method, fmt.Sprintf("%d", ww.status)).Observe(duration)
		})
	}
}

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(status int) {
	w.status = status
	w.ResponseWriter.WriteHeader(status)
}
