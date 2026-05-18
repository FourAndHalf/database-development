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
	CREATE TABLE IF NOT EXISTS users (
		id UUID PRIMARY KEY,
		email TEXT UNIQUE NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS conversations (
		id UUID PRIMARY KEY,
		user_id UUID REFERENCES users(id) ON DELETE CASCADE,
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

		CREATE TABLE IF NOT EXISTS papers (
		id UUID PRIMARY KEY,
		title TEXT NOT NULL,
		filename TEXT UNIQUE NOT NULL,
		url TEXT,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS authors (
		id UUID PRIMARY KEY,
		name TEXT NOT NULL UNIQUE
	);

	CREATE TABLE IF NOT EXISTS paper_authors (
		paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
		author_id UUID REFERENCES authors(id) ON DELETE CASCADE,
		PRIMARY KEY (paper_id, author_id)
	);

	CREATE TABLE IF NOT EXISTS paper_metadata (
		paper_id UUID PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
		data JSONB NOT NULL DEFAULT '{}'::jsonb,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);
	`
	_, err := s.db.Exec(query)
	return err
}

func (s *Store) EnsureConversation(ctx context.Context, id, userID, title string) error {
	var userVal interface{}
	if userID != "" && userID != "00000000-0000-0000-0000-000000000000" {
		userVal = userID
	} else {
		userVal = nil
	}

	query := `INSERT INTO conversations (id, user_id, title) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING`
	_, err := s.db.ExecContext(ctx, query, id, userVal, title)
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

func (s *Store) GetConversationMessages(ctx context.Context, conversationID string) ([]Message, error) {
	query := `
		SELECT id, conversation_id, role, text, created_at
		FROM messages
		WHERE conversation_id = $1
		ORDER BY created_at ASC
	`
	rows, err := s.db.QueryContext(ctx, query, conversationID)
	if err != nil {
		return nil, fmt.Errorf("failed to get messages: %w", err)
	}
	defer rows.Close()

	var msgs []Message
	for rows.Next() {
		var m Message
		if err := rows.Scan(&m.ID, &m.ConversationID, &m.Role, &m.Text, &m.CreatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan message: %w", err)
		}
		msgs = append(msgs, m)
	}
	return msgs, nil
}

func (s *Store) ConversationExists(ctx context.Context, conversationID string) (bool, error) {
	query := `SELECT EXISTS(SELECT 1 FROM conversations WHERE id = $1)`
	var exists bool
	if err := s.db.QueryRowContext(ctx, query, conversationID).Scan(&exists); err != nil {
		return false, fmt.Errorf("failed to check conversation existence: %w", err)
	}
	return exists, nil
}
