package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"database-development/apps/api-go/internal/httpserver"
	"database-development/apps/api-go/internal/rag"
	"database-development/apps/api-go/internal/store"
	"database-development/apps/api-go/internal/telemetry"
)

func main() {
	port := envInt("PORT", 8080)
	uiOrigin := envString("UI_ORIGIN", "http://localhost:4200")
	ragEngineType := envString("RAG_ENGINE", "chroma")
	pythonServiceURL := envString("PYTHON_SERVICE_URL", "http://localhost:8000")

	logger := log.New(os.Stdout, "api ", log.LstdFlags|log.Lmicroseconds)

	// OpenTelemetry Initialization
	otelCtx, otelStop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer otelStop()

	shutdown, err := telemetry.InitTracer(otelCtx)
	if err != nil {
		logger.Printf("warning: failed to initialize telemetry: %v", err)
	} else {
		defer func() {
			if err := shutdown(context.Background()); err != nil {
				logger.Printf("error shutting down tracer: %v", err)
			}
		}()
	}

	dbURL := envString("DB_URL", "postgres://nexus:PinkFloyd@localhost:5434/nexus_db?sslmode=disable")
	dbStore, err := store.New(dbURL)
	if err != nil {
		logger.Fatalf("failed to connect to db: %v", err)
	}
	defer dbStore.Close()

	var engine rag.Engine
	switch ragEngineType {
	// "chroma" and "real" both select the Python RAG proxy. The vector backend
	// (Chroma) lives inside the Python service, not here — these are aliases so
	// the RAG_ENGINE env value can't silently fall through to mock.
	case "chroma", "real":
		engine = rag.NewChromaEngine(pythonServiceURL)
		logger.Printf("using RAG engine: %s -> python proxy (%s)", ragEngineType, pythonServiceURL)
	case "mock":
		engine = rag.NewMockEngine()
		logger.Printf("using RAG engine: mock")
	default:
		logger.Printf("warning: unknown RAG_ENGINE %q, defaulting to python proxy (%s)", ragEngineType, pythonServiceURL)
		engine = rag.NewChromaEngine(pythonServiceURL)
	}

	srv := httpserver.New(httpserver.Config{
		Logger:           logger,
		Engine:           engine,
		Store:            dbStore,
		UIOrigin:         uiOrigin,
		PythonServiceURL: pythonServiceURL,
	})

	httpServer := &http.Server{
		Addr:              ":" + strconv.Itoa(port),
		Handler:           srv.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       120 * time.Second,
		WriteTimeout:      120 * time.Second,
		IdleTimeout:       120 * time.Second,
	}

	go func() {
		logger.Printf("listening on http://localhost:%d (CORS origin: %s)", port, uiOrigin)
		if err := httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Fatalf("listen: %v", err)
		}
	}()

	<-otelCtx.Done()
	logger.Printf("shutting down...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = httpServer.Shutdown(shutdownCtx)
}

func envString(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		n, err := strconv.Atoi(v)
		if err == nil {
			return n
		}
	}
	return def
}
