package rag

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"time"

	"database-development/apps/api-go/internal/middleware"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

type pythonProxyEngine struct {
	pythonServiceURL string
	httpClient       *http.Client
}

func NewPythonProxyEngine(pythonServiceURL string) Engine {
	return &pythonProxyEngine{
		pythonServiceURL: pythonServiceURL,
		httpClient: &http.Client{
			Timeout: 600 * time.Second,
			// otelhttp injects the W3C traceparent header so the Python engine
			// continues the same trace instead of starting a disconnected one.
			Transport: otelhttp.NewTransport(http.DefaultTransport),
		},
	}
}

type pythonQueryRequest struct {
	Query          string `json:"query"`
	NResults       int    `json:"n_results"`
	Model          string `json:"model"`
	History        []Turn `json:"history,omitempty"`
	ConversationID string `json:"conversation_id,omitempty"`
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

func (e *pythonProxyEngine) Answer(ctx context.Context, q Question) (Answer, error) {
	reqBody, err := json.Marshal(pythonQueryRequest{
		Query:          q.Message,
		NResults:       5,
		Model:          q.Model,
		History:        q.History,
		ConversationID: q.ConversationID,
	})
	if err != nil {
		return Answer{}, err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", e.pythonServiceURL+"/api/query", bytes.NewBuffer(reqBody))
	if err != nil {
		return Answer{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	if rid := middleware.RequestIDFromContext(ctx); rid != "" {
		req.Header.Set("X-Request-ID", rid)
	}

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

func (e *pythonProxyEngine) DeleteDocument(ctx context.Context, filename string) error {
	req, err := http.NewRequestWithContext(ctx, "DELETE", e.pythonServiceURL+"/api/papers/"+filename, nil)
	if err != nil {
		return err
	}
	if rid := middleware.RequestIDFromContext(ctx); rid != "" {
		req.Header.Set("X-Request-ID", rid)
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

func (e *pythonProxyEngine) ValidatePaper(ctx context.Context, r io.Reader, filename string) error {
	var b bytes.Buffer
	mw := multipart.NewWriter(&b)
	part, err := mw.CreateFormFile("file", filename)
	if err != nil {
		return err
	}
	if _, err := io.Copy(part, r); err != nil {
		return err
	}
	mw.Close()

	req, err := http.NewRequestWithContext(ctx, "POST", e.pythonServiceURL+"/api/papers/validate", &b)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", mw.FormDataContentType())

	resp, err := e.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to call python validation: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("python validation returned %s", resp.Status)
	}
	
	var res struct {
		Valid  bool   `json:"valid"`
		Reason string `json:"reason"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return err
	}
	if !res.Valid {
		return fmt.Errorf("validation failed: %s", res.Reason)
	}
	return nil
}
