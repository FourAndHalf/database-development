package store

import (
	"time"
)

type User struct {
	ID           string    `json:"id"`
	Email        string    `json:"email"`
	Username     *string   `json:"username,omitempty"`
	PasswordHash string    `json:"-"`
	IsAdmin      bool      `json:"is_admin"`
	LoginCount   int       `json:"login_count"`
	CreatedAt    time.Time `json:"created_at"`
}

type Conversation struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id,omitempty"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
}

type Message struct {
	ID             string    `json:"id"`
	ConversationID string    `json:"conversation_id"`
	Role           string    `json:"role"`
	Text           string    `json:"content"`
	CreatedAt      time.Time `json:"created_at"`
}

type Paper struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	Filename  string    `json:"filename"`
	URL       string    `json:"url,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Author struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type PaperMetadata struct {
	PaperID   string                 `json:"paper_id"`
	Data      map[string]interface{} `json:"data"`
	UpdatedAt time.Time              `json:"updated_at"`
}

type PaperDetail struct {
	Paper
	Authors  []Author               `json:"authors"`
	Metadata map[string]interface{} `json:"metadata"`
}

type PaginatedPapers struct {
	Papers []PaperDetail `json:"papers"`
	Total  int           `json:"total"`
}
