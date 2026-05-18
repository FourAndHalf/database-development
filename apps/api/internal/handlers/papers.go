package handlers

import (
	"encoding/json"
	"log"
	"net/http"

	"database-development/apps/api/internal/store"
)

type PaperHandler struct {
	logger *log.Logger
	store  *store.Store
}

func NewPaperHandler(logger *log.Logger, s *store.Store) *PaperHandler {
	return &PaperHandler{logger: logger, store: s}
}

func (h *PaperHandler) GetPaper(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	id := r.PathValue("id")
	if id == "" {
		writeErr(w, http.StatusBadRequest, "missing_paper_id")
		return
	}

	pd, err := h.store.GetPaperWithMetadata(ctx, id)
	if err != nil {
		h.logger.Printf("Failed to get paper %s: %v", id, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	if pd == nil {
		writeErr(w, http.StatusNotFound, "paper_not_found")
		return
	}

	writeJSON(w, http.StatusOK, pd)
}

func (h *PaperHandler) PutMetadata(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	id := r.PathValue("id")
	if id == "" {
		writeErr(w, http.StatusBadRequest, "missing_paper_id")
		return
	}

	var metadata map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&metadata); err != nil {
		h.logger.Printf("Failed to decode metadata for paper %s: %v", id, err)
		writeErr(w, http.StatusBadRequest, "invalid_json")
		return
	}

	if err := h.store.UpdateMetadata(ctx, id, metadata); err != nil {
		h.logger.Printf("Failed to update metadata for paper %s: %v", id, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "updated"})
}
