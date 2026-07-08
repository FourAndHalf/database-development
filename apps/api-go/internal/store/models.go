package store

import (
	"encoding/json"
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
	ID             string          `json:"id"`
	ConversationID string          `json:"conversation_id"`
	Role           string          `json:"role"`
	Text           string          `json:"content"`
	Sources        json.RawMessage `json:"sources,omitempty"`
	CreatedAt      time.Time       `json:"created_at"`
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

type DailyMetric struct {
	ID               int       `json:"id"`
	MetricDate       string    `json:"metric_date"`
	TotalQueries     int       `json:"total_queries"`
	SuccessfulQueries int      `json:"successful_queries"`
	FailedQueries    int       `json:"failed_queries"`
	FailureRate      float64   `json:"failure_rate"`
	P50LatencyMs     float64   `json:"p50_latency_ms"`
	P95LatencyMs     float64   `json:"p95_latency_ms"`
	P99LatencyMs     float64   `json:"p99_latency_ms"`
	AvgLatencyMs     float64   `json:"avg_latency_ms"`
	MinLatencyMs     float64   `json:"min_latency_ms"`
	MaxLatencyMs     float64   `json:"max_latency_ms"`
	CreatedAt        time.Time `json:"created_at"`
	UpdatedAt        time.Time `json:"updated_at"`
}
