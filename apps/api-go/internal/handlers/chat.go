package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"
	"time"

	"database-development/apps/api-go/internal/rag"
	"database-development/apps/api-go/internal/store"
	"database-development/apps/api-go/internal/util"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
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
	ConversationID string     `json:"conversation_id"`
	UserID         string     `json:"user_id"`
	Message        string     `json:"message"`
	Model          string     `json:"model"`
	History        []rag.Turn `json:"history"`
}

type chatResponse struct {
	ConversationID string       `json:"conversation_id"`
	UserID         string       `json:"user_id,omitempty"`
	Answer         string       `json:"answer"`
	Sources        []rag.Source `json:"sources,omitempty"`
	LatencyMs      int64        `json:"latency_ms"`
	Mock           bool         `json:"mock"`
}

func (h *ChatHandler) GetMessages(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	id := r.PathValue("id")
	if id == "" {
		writeErr(w, http.StatusBadRequest, "missing_conversation_id")
		return
	}

	msgs, err := h.store.GetConversationMessages(ctx, id)
	if err != nil {
		h.logger.Printf("Failed to get messages for conversation %s: %v", id, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, msgs)
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
	if conversationID == "" || len(conversationID) != 36 {
		conversationID = util.NewID()
	}

	// Extract userID from context (set by authMiddleware)
	userID, _ := ctx.Value(store.UserIDKey).(string)
	isAuth := userID != ""

	// Enrich the server span so chats are filterable in OpenObserve.
	trace.SpanFromContext(ctx).SetAttributes(
		attribute.String("chat.conversation_id", conversationID),
		attribute.String("chat.model", req.Model),
		attribute.Bool("chat.authenticated", isAuth),
		attribute.Int("chat.message_len", len(req.Message)),
	)

	if isAuth {
		// Ensure the conversation actually exists in the database
		if err := h.store.EnsureConversation(ctx, conversationID, userID, util.TruncateTitle(req.Message, 50)); err != nil {
			h.logger.Printf("Failed to ensure conversation: %v", err)
			writeErr(w, http.StatusInternalServerError, "db_error")
			return
		}

		if err := h.store.SaveMessage(ctx, conversationID, "user", req.Message); err != nil {
			h.logger.Printf("Failed to save user message: %v", err)
			writeErr(w, http.StatusInternalServerError, "db_error")
			return
		}
	}

	ans, err := h.engine.Answer(ctx, rag.Question{
		ConversationID: conversationID,
		Message:        req.Message,
		Model:          req.Model,
		History:        req.History,
	})
	if err != nil {
		if errors.Is(err, rag.ErrNoAnswer) {
			writeErr(w, http.StatusUnprocessableEntity, "no_answer")
			return
		}
		h.logger.Printf("RAG engine failed to answer: %v", err)
		writeErr(w, http.StatusInternalServerError, "chat_failed")
		go func() {
			bgCtx := context.Background()
			elapsed := time.Since(start).Milliseconds()
			if err := h.store.RecordQueryMetric(bgCtx, elapsed, false); err != nil {
				h.logger.Printf("Failed to record query metric: %v", err)
			}
		}()
		return
	}

	if isAuth {
		if err := h.store.SaveMessage(ctx, conversationID, "assistant", ans.Text); err != nil {
			h.logger.Printf("Failed to save assistant message (non-fatal): %v", err)
		}
	}

	resp := chatResponse{
		ConversationID: conversationID,
		UserID:         userID,
		Answer:         ans.Text,
		Sources:        ans.Sources,
		LatencyMs:      time.Since(start).Milliseconds(),
		Mock:           ans.Mock,
	}
	writeJSON(w, http.StatusOK, resp)

	go func() {
		bgCtx := context.Background()
		if err := h.store.RecordQueryMetric(bgCtx, resp.LatencyMs, true); err != nil {
			h.logger.Printf("Failed to record query metric: %v", err)
		}
	}()
}

func writeErr(w http.ResponseWriter, status int, code string) {
	writeJSON(w, status, map[string]any{"error": code})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
