package rag

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type chromaEngine struct {
	pythonServiceURL string
	httpClient       *http.Client
}

func NewChromaEngine(pythonServiceURL string) Engine {
	return &chromaEngine{
		pythonServiceURL: pythonServiceURL,
		httpClient: &http.Client{
			Timeout: 600 * time.Second,
		},
	}
}

type pythonQueryRequest struct {
	Query    string `json:"query"`
	NResults int    `json:"n_results"`
	Model    string `json:"model"`
}

type pythonSource struct {
	SourceFile string  `json:"source_file"`
	Content    string  `json:"content"`
	Distance   float64 `json:"distance"`
	URL        string  `json:"url,omitempty"`
}

type pythonQueryResponse struct {
	Answer  string         `json:"answer"`
	Sources []pythonSource `json:"sources"`
}

func (e *chromaEngine) Answer(ctx context.Context, q Question) (Answer, error) {
	reqBody, err := json.Marshal(pythonQueryRequest{
		Query:    q.Message,
		NResults: 5,
		Model:    q.Model,
	})
	if err != nil {
		return Answer{}, err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", e.pythonServiceURL+"/api/query", bytes.NewBuffer(reqBody))
	if err != nil {
		return Answer{}, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := e.httpClient.Do(req)
	if err != nil {
		return Answer{}, fmt.Errorf("failed to call python service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return Answer{}, fmt.Errorf("python service returned status: %s", resp.Status)
	}

	var pyResp pythonQueryResponse
	if err := json.NewDecoder(resp.Body).Decode(&pyResp); err != nil {
		return Answer{}, err
	}

	sources := make([]Source, len(pyResp.Sources))
	for i, s := range pyResp.Sources {
		sources[i] = Source{
			PaperID: s.SourceFile,
			Title:   s.SourceFile, // Using filename or web title
			Snippet: s.Content,
			URL:     s.URL,
		}
	}

	return Answer{
		Text:    pyResp.Answer,
		Sources: sources,
		Mock:    false,
	}, nil
}

func (e *chromaEngine) DeleteDocument(ctx context.Context, filename string) error {
	req, err := http.NewRequestWithContext(ctx, "DELETE", e.pythonServiceURL+"/api/papers/"+filename, nil)
	if err != nil {
		return err
	}

	resp, err := e.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to call python service to delete: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("python service returned status: %s", resp.Status)
	}

	return nil
}
