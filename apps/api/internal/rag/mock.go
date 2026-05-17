package rag

import (
	"context"
	"strings"
	"time"
)

type mockEngine struct{}

func NewMockEngine() Engine { return &mockEngine{} }

func (m *mockEngine) Answer(ctx context.Context, q Question) (Answer, error) {
	// Simulate retrieval/LLM latency.
	select {
	case <-time.After(250 * time.Millisecond):
	case <-ctx.Done():
		return Answer{}, ctx.Err()
	}

	msg := strings.TrimSpace(q.Message)
	if msg == "" {
		return Answer{}, ErrNoAnswer
	}

	// Mock: return an answer that looks like a grounded response with citations.
	return Answer{
		Text: "Mock answer (RAG not wired yet). You asked:\n\n" + msg + "\n\nNext step: connect retrieval (vector + BM25), reranking, and an LLM call, then populate `sources` from retrieved chunks.",
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

