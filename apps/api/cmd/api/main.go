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

	"database-development/apps/api/internal/httpserver"
	"database-development/apps/api/internal/rag"
	"database-development/apps/api/internal/store"
)

func main() {
	port := envInt("PORT", 8080)
	uiOrigin := envString("UI_ORIGIN", "http://localhost:4200")
	ragEngineType := envString("RAG_ENGINE", "mock")
	pythonServiceURL := envString("PYTHON_SERVICE_URL", "http://localhost:8000")

	logger := log.New(os.Stdout, "api ", log.LstdFlags|log.Lmicroseconds)
	
	dbStore, err := store.New("postgres://nexus:password@localhost:5434/nexus_db?sslmode=disable")
	if err != nil {
		logger.Fatalf("failed to connect to db: %v", err)
	}
	defer dbStore.Close()

	var engine rag.Engine
	switch ragEngineType {
	case "chroma":
		engine = rag.NewChromaEngine(pythonServiceURL)
		logger.Printf("using RAG engine: chroma (python service: %s)", pythonServiceURL)
	default:
		engine = rag.NewMockEngine()
		logger.Printf("using RAG engine: mock")
	}

	srv := httpserver.New(httpserver.Config{
		Logger:   logger,
		Engine:   engine,
		Store:    dbStore,
		UIOrigin: uiOrigin,
	})

	httpServer := &http.Server{
		Addr:              ":" + strconv.Itoa(port),
		Handler:           srv.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	go func() {
		logger.Printf("listening on http://localhost:%d (CORS origin: %s)", port, uiOrigin)
		if err := httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Fatalf("listen: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	logger.Printf("shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = httpServer.Shutdown(ctx)
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
