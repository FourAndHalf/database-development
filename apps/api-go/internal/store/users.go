package store

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/google/uuid"
)

func (s *Store) CreateUser(ctx context.Context, email, passwordHash string, username *string) (string, error) {
	query := `INSERT INTO users (email, password_hash, username) VALUES ($1, $2, $3) RETURNING id`
	var actualID string
	err := s.db.QueryRowContext(ctx, query, email, passwordHash, username).Scan(&actualID)
	if err != nil {
		return "", fmt.Errorf("failed to create user: %w", err)
	}
	return actualID, nil
}

const userColumns = `id, email, username, password_hash, is_admin, login_count, created_at`

func scanUser(row interface{ Scan(...interface{}) error }) (*User, error) {
	var u User
	err := row.Scan(&u.ID, &u.Email, &u.Username, &u.PasswordHash, &u.IsAdmin, &u.LoginCount, &u.CreatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get user: %w", err)
	}
	return &u, nil
}

func (s *Store) GetUserByID(ctx context.Context, id string) (*User, error) {
	return scanUser(s.db.QueryRowContext(ctx, `SELECT `+userColumns+` FROM users WHERE id = $1`, id))
}

func (s *Store) GetUserByEmail(ctx context.Context, email string) (*User, error) {
	return scanUser(s.db.QueryRowContext(ctx, `SELECT `+userColumns+` FROM users WHERE email = $1`, email))
}

// RecordLogin bumps login_count + last_login_at via the schema helper function.
func (s *Store) RecordLogin(ctx context.Context, userID string) error {
	if _, err := s.db.ExecContext(ctx, `SELECT record_login($1)`, userID); err != nil {
		return fmt.Errorf("failed to record login: %w", err)
	}
	return nil
}

func (s *Store) UpsertUser(ctx context.Context, email string) (string, error) {
	id := uuid.New().String()
	query := `
		INSERT INTO users (id, email)
		VALUES ($1, $2)
		ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
		RETURNING id
	`
	var actualID string
	err := s.db.QueryRowContext(ctx, query, id, email).Scan(&actualID)
	if err != nil {
		return "", fmt.Errorf("failed to upsert user: %w", err)
	}
	return actualID, nil
}

func (s *Store) GetLastConversations(ctx context.Context, userID string, limit int) ([]Conversation, error) {
	var rows *sql.Rows
	var err error

	if userID == "00000000-0000-0000-0000-000000000000" {
		query := `
			SELECT id, user_id, title, created_at
			FROM conversations
			ORDER BY created_at DESC
			LIMIT $1
		`
		rows, err = s.db.QueryContext(ctx, query, limit)
	} else {
		query := `
			SELECT id, user_id, title, created_at
			FROM conversations
			WHERE user_id = $1
			ORDER BY created_at DESC
			LIMIT $2
		`
		rows, err = s.db.QueryContext(ctx, query, userID, limit)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to get last conversations: %w", err)
	}
	defer rows.Close()

	var convs []Conversation
	for rows.Next() {
		var c Conversation
		if err := rows.Scan(&c.ID, &c.UserID, &c.Title, &c.CreatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan conversation: %w", err)
		}
		convs = append(convs, c)
	}
	return convs, nil
}

func (s *Store) DeleteConversation(ctx context.Context, conversationID, userID string) error {
	query := `DELETE FROM conversations WHERE id = $1 AND user_id = $2`
	_, err := s.db.ExecContext(ctx, query, conversationID, userID)
	if err != nil {
		return fmt.Errorf("failed to delete conversation: %w", err)
	}
	return nil
}
