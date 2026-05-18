package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"database-development/apps/api/internal/store"
	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
)

var jwtSecret = []byte("aether-secret-key") // In production, use an environment variable

type AuthHandler struct {
	logger *log.Logger
	store  *store.Store
}

func NewAuthHandler(logger *log.Logger, s *store.Store) *AuthHandler {
	return &AuthHandler{logger: logger, store: s}
}

type authRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type authResponse struct {
	Token string `json:"token"`
	Email string `json:"email"`
	ID    string `json:"id"`
}

func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	var req authRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid_json")
		return
	}

	if req.Email == "" || req.Password == "" {
		writeErr(w, http.StatusBadRequest, "email_and_password_required")
		return
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		h.logger.Printf("Failed to hash password: %v", err)
		writeErr(w, http.StatusInternalServerError, "internal_error")
		return
	}

	id, err := h.store.CreateUser(ctx, req.Email, string(hash))
	if err != nil {
		h.logger.Printf("Failed to create user: %v", err)
		writeErr(w, http.StatusConflict, "user_already_exists")
		return
	}

	token, err := createToken(id, req.Email)
	if err != nil {
		h.logger.Printf("Failed to create token: %v", err)
		writeErr(w, http.StatusInternalServerError, "token_error")
		return
	}

	writeJSON(w, http.StatusCreated, authResponse{
		Token: token,
		Email: req.Email,
		ID:    id,
	})
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	var req authRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid_json")
		return
	}

	u, err := h.store.GetUserByEmail(ctx, req.Email)
	if err != nil {
		h.logger.Printf("Failed to get user: %v", err)
		writeErr(w, http.StatusInternalServerError, "internal_error")
		return
	}

	if u == nil {
		writeErr(w, http.StatusUnauthorized, "invalid_credentials")
		return
	}

	if err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(req.Password)); err != nil {
		writeErr(w, http.StatusUnauthorized, "invalid_credentials")
		return
	}

	token, err := createToken(u.ID, u.Email)
	if err != nil {
		h.logger.Printf("Failed to create token: %v", err)
		writeErr(w, http.StatusInternalServerError, "token_error")
		return
	}

	writeJSON(w, http.StatusOK, authResponse{
		Token: token,
		Email: u.Email,
		ID:    u.ID,
	})
}

func createToken(userID, email string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":   userID,
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24 * 7).Unix(), // 1 week
	})

	return token.SignedString(jwtSecret)
}
