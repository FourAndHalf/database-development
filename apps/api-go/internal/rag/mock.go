package rag

import (
	"context"
	"io"
	"strings"
	"time"
)

type mockEngine struct{}

func NewMockEngine() Engine { return &mockEngine{} }

func (m *mockEngine) AnswerStream(ctx context.Context, q Question, onToken func(text string)) (Answer, error) {
	msg := strings.TrimSpace(q.Message)
	if msg == "" {
		return Answer{}, ErrNoAnswer
	}

	text := "Mock answer (RAG not wired yet). You asked:\n\n" + msg + "\n\nNext step: connect retrieval (vector + BM25), reranking, and an LLM call, then populate `sources` from retrieved chunks."

	// Simulate token-by-token generation latency in small chunks.
	for i := 0; i < len(text); i += 20 {
		end := i + 20
		if end > len(text) {
			end = len(text)
		}
		select {
		case <-time.After(30 * time.Millisecond):
			onToken(text[i:end])
		case <-ctx.Done():
			return Answer{}, ctx.Err()
		}
	}

	// Mock: return an answer that looks like a grounded response with citations.
	return Answer{
		Text: text,
		Sources: []Source{
			{
				PaperID: "spanner-2012",
				Title:   "Spanner: Google’s Globally-Distributed Database",
				Page:    3,
				Snippet: "Spanner assigns globally meaningful commit timestamps and provides externally consistent reads/writes.",
			},
			{
				PaperID: "dynamo-2007",
				Title:   "Dynamo: Amazon’s Highly Available Key-value Store",
				Page:    2,
				Snippet: "Dynamo targets high availability using techniques like consistent hashing and quorum-like replication.",
			},
		},
		Mock: true,
	}, nil
}

func (m *mockEngine) DeleteDocument(ctx context.Context, filename string) error {
	return nil
}

func (m *mockEngine) ValidatePaper(ctx context.Context, r io.Reader, filename string) error {
	return nil
}
