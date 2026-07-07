package handlers

import (
	"net/http"
	"time"
	"log"

	"database-development/apps/api-go/internal/store"
)

type MetricsHandler struct {
	logger    *log.Logger
	store     *store.Store
	startTime time.Time
}

func NewMetricsHandler(logger *log.Logger, s *store.Store) *MetricsHandler {
	return &MetricsHandler{logger: logger, store: s, startTime: time.Now()}
}

func (h *MetricsHandler) GetDashboard(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	today, err := h.store.GetTodayMetrics(ctx)
	if err != nil {
		h.logger.Printf("Failed to get today metrics: %v", err)
	}

	history, err := h.store.GetDailyMetrics(ctx, 30)
	if err != nil {
		h.logger.Printf("Failed to get daily metrics: %v", err)
		history = []store.DailyMetric{}
	}

	uptime := time.Since(h.startTime).Seconds()

	result := map[string]any{
		"realtime": map[string]any{
			"uptime_s": uptime,
		},
		"today":   today,
		"history": history,
		"date":    time.Now().UTC().Format("2006-01-02"),
	}

	writeJSON(w, http.StatusOK, result)
}
