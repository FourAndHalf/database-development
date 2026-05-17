package store

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

type Store struct {
	db *sql.DB
}

type Conversation struct {
	ID        string
	Title     string
	CreatedAt time.Time
}

type Message struct {
	ID             string
	ConversationID string
	Role           string
	Text           string
	CreatedAt      time.Time
}

func New(connStr string) (*Store, error) {
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, err
	}

	// Set connection pool limits
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	if err := db.Ping(); err != nil {
		return nil, err
	}

	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		return nil, err
	}

	return s, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) migrate() error {
	query := `
	CREATE TABLE IF NOT EXISTS conversations (
		id UUID PRIMARY KEY,
		title TEXT NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS messages (
		id UUID PRIMARY KEY,
		conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
		role TEXT NOT NULL,
		text TEXT NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);
	`
	_, err := s.db.Exec(query)
	return err
}

func (s *Store) EnsureConversation(ctx context.Context, id, title string) error {
	// ON CONFLICT DO NOTHING ensures that if the client sends an ID that 
	// already exists, we simply proceed. If it doesn't exist (like a cached ID 
	// from the frontend on a fresh database), it creates it.
	query := `INSERT INTO conversations (id, title) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING`
	_, err := s.db.ExecContext(ctx, query, id, title)
	if err != nil {
		return fmt.Errorf("failed to ensure conversation: %w", err)
	}
	return nil
}

func (s *Store) SaveMessage(ctx context.Context, conversationID, role, text string) error {
	id := uuid.New().String()
	query := `INSERT INTO messages (id, conversation_id, role, text) VALUES ($1, $2, $3, $4)`
	_, err := s.db.ExecContext(ctx, query, id, conversationID, role, text)
	if err != nil {
		return fmt.Errorf("failed to save message: %w", err)
	}
	return nil
}

func (s *Store) ConversationExists(ctx context.Context, conversationID string) (bool, error) {
	query := `SELECT EXISTS(SELECT 1 FROM conversations WHERE id = $1)`
	var exists bool
	if err := s.db.QueryRowContext(ctx, query, conversationID).Scan(&exists); err != nil {
		return false, fmt.Errorf("failed to check conversation existence: %w", err)
	}
	return exists, nil
}
