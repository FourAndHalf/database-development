package rag

import (
	"context"
	"errors"
)

var ErrNoAnswer = errors.New("no answer")

type Engine interface {
	Answer(ctx context.Context, q Question) (Answer, error)
	DeleteDocument(ctx context.Context, filename string) error
}

type Question struct {
	ConversationID string
	Message        string
	Model          string
}

type Answer struct {
	Text    string
	Sources []Source
	Mock    bool
}

type Source struct {
	PaperID string `json:"paper_id"`
	Title   string `json:"title"`
	Page    int    `json:"page"`
	Snippet string `json:"snippet"`
	URL     string `json:"url,omitempty"`
}
