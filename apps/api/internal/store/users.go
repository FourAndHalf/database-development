package store

import (
	"context"
	"fmt"

	"github.com/google/uuid"
)

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
	query := `
		SELECT id, user_id, title, created_at
		FROM conversations
		WHERE user_id = $1
		ORDER BY created_at DESC
		LIMIT $2
	`
	rows, err := s.db.QueryContext(ctx, query, userID, limit)
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
