package handlers

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"
	"time"

	"database-development/apps/api/internal/rag"
	"database-development/apps/api/internal/store"
	"database-development/apps/api/internal/util"
)

type ChatHandler struct {
	logger *log.Logger
	engine rag.Engine
	store  *store.Store
}

func NewChatHandler(logger *log.Logger, engine rag.Engine, s *store.Store) *ChatHandler {
	return &ChatHandler{logger: logger, engine: engine, store: s}
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
	ctx := r.Context()

	var req chatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.logger.Printf("Failed to decode chat request: %v", err)
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
		newID, err := h.store.CreateConversation(ctx, util.TruncateTitle(req.Message, 50))
		if err != nil {
			h.logger.Printf("Failed to create conversation: %v", err)
			writeErr(w, http.StatusInternalServerError, "db_error")
			return
		}
		conversationID = newID
	}

	if err := h.store.SaveMessage(ctx, conversationID, "user", req.Message); err != nil {
		h.logger.Printf("Failed to save user message: %v", err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	ans, err := h.engine.Answer(ctx, rag.Question{
		ConversationID: conversationID,
		Message:        req.Message,
	})
	if err != nil {
		if errors.Is(err, rag.ErrNoAnswer) {
			writeErr(w, http.StatusUnprocessableEntity, "no_answer")
			return
		}
		h.logger.Printf("RAG engine failed to answer: %v", err)
		writeErr(w, http.StatusInternalServerError, "chat_failed")
		return
	}

	if err := h.store.SaveMessage(ctx, conversationID, "assistant", ans.Text); err != nil {
		h.logger.Printf("Failed to save assistant message (non-fatal): %v", err)
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

