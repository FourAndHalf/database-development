package httpserver

import (
	"log"
	"net/http"

	"database-development/apps/api/internal/handlers"
	"database-development/apps/api/internal/rag"
)

type Config struct {
	Logger   *log.Logger
	Engine   rag.Engine
	UIOrigin string
}

type Server struct {
	cfg Config
	mux http.Handler
}

func New(cfg Config) *Server {
	if cfg.Logger == nil {
		cfg.Logger = log.Default()
	}
	if cfg.UIOrigin == "" {
		cfg.UIOrigin = "http://localhost:4200"
	}

	s := &Server{cfg: cfg}
	s.mux = s.routes()
	return s
}

func (s *Server) Handler() http.Handler {
	return s.mux
}

func (s *Server) routes() http.Handler {
	health := handlers.NewHealthHandler()
	chat := handlers.NewChatHandler(s.cfg.Engine)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", health.Get)
	mux.HandleFunc("OPTIONS /v1/chat", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("POST /v1/chat", chat.Post)

	return chain(
		mux,
		recoverMiddleware(s.cfg.Logger),
		requestLogMiddleware(s.cfg.Logger),
		corsMiddleware(s.cfg.UIOrigin),
	)
}

