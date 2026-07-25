package rag

import (
	"context"
	"errors"
	"io"
)

var ErrNoAnswer = errors.New("no answer")

type Engine interface {
	// AnswerStream streams raw text tokens to onToken as they arrive, then returns
	// the final Answer (full text + sources) once generation completes.
	AnswerStream(ctx context.Context, q Question, onToken func(text string)) (Answer, error)
	DeleteDocument(ctx context.Context, filename string) error
	ValidatePaper(ctx context.Context, r io.Reader, filename string) error
}

type Turn struct {
	Role string `json:"role"`
	Text string `json:"text"`
}

type Question struct {
	ConversationID string
	Message        string
	Model          string
	History        []Turn
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
