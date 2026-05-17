package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"

	"database-development/apps/api/internal/rag"
	"database-development/apps/api/internal/util"
)

type ChatHandler struct {
	engine rag.Engine
}

func NewChatHandler(engine rag.Engine) *ChatHandler {
	return &ChatHandler{engine: engine}
}

type chatRequest struct {
	ConversationID string `json:"conversation_id"`
	Message        string `json:"message"`
}

type chatResponse struct {
	ConversationID string        `json:"conversation_id"`
	Answer         string        `json:"answer"`
	Sources        []rag.Source  `json:"sources,omitempty"`
	LatencyMs      int64         `json:"latency_ms"`
	Mock           bool          `json:"mock"`
}

func (h *ChatHandler) Post(w http.ResponseWriter, r *http.Request) {
	start := time.Now()

	var req chatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid_json")
		return
	}

	req.Message = strings.TrimSpace(req.Message)
	if req.Message == "" {
		writeErr(w, http.StatusBadRequest, "message_required")
		return
	}

	conversationID := strings.TrimSpace(req.ConversationID)
	if conversationID == "" {
		conversationID = util.NewID()
	}

	ans, err := h.engine.Answer(r.Context(), rag.Question{
		ConversationID: conversationID,
		Message:        req.Message,
	})
	if err != nil {
		if errors.Is(err, rag.ErrNoAnswer) {
			writeErr(w, http.StatusUnprocessableEntity, "no_answer")
			return
		}
		writeErr(w, http.StatusInternalServerError, "chat_failed")
		return
	}

	resp := chatResponse{
		ConversationID: conversationID,
		Answer:         ans.Text,
		Sources:        ans.Sources,
		LatencyMs:      time.Since(start).Milliseconds(),
		Mock:           ans.Mock,
	}
	writeJSON(w, http.StatusOK, resp)
}

func writeErr(w http.ResponseWriter, status int, code string) {
	writeJSON(w, status, map[string]any{"error": code})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

