package handlers

import (
	"encoding/json"
	"log"
	"net/http"

	"database-development/apps/api-go/internal/store"
)

type UserHandler struct {
	logger *log.Logger
	store  *store.Store
}

func NewUserHandler(logger *log.Logger, s *store.Store) *UserHandler {
	return &UserHandler{logger: logger, store: s}
}

func (h *UserHandler) PutUser(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	var req struct {
		Email string `json:"email"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid_json")
		return
	}

	id, err := h.store.UpsertUser(ctx, req.Email)
	if err != nil {
		h.logger.Printf("Failed to upsert user %s: %v", req.Email, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"id": id})
}

func (h *UserHandler) GetHistory(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	userID := r.PathValue("id")
	if userID == "" {
		writeErr(w, http.StatusBadRequest, "missing_user_id")
		return
	}

	// Fetch last 5 conversations
	history, err := h.store.GetLastConversations(ctx, userID, 5)
	if err != nil {
		h.logger.Printf("Failed to get history for user %s: %v", userID, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, history)
}

func (h *UserHandler) DeleteChat(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	userID := r.PathValue("id")
	conversationID := r.PathValue("conversation_id")

	if userID == "" || conversationID == "" {
		writeErr(w, http.StatusBadRequest, "missing_ids")
		return
	}

	if err := h.store.DeleteConversation(ctx, conversationID, userID); err != nil {
		h.logger.Printf("Failed to delete chat %s for user %s: %v", conversationID, userID, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "deleted"})
}
