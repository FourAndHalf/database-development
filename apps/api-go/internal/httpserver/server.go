package httpserver

import (
	"log"
	"net/http"

	"database-development/apps/api-go/internal/handlers"
	"database-development/apps/api-go/internal/middleware"
	"database-development/apps/api-go/internal/rag"
	"database-development/apps/api-go/internal/store"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

type Config struct {
	Logger           *log.Logger
	Engine           rag.Engine
	Store            *store.Store
	UIOrigin         string
	PythonServiceURL string
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
	return otelhttp.NewHandler(s.mux, "rag-go-api")
}
func (s *Server) routes() http.Handler {
	health := handlers.NewHealthHandler()
	chat := handlers.NewChatHandler(s.cfg.Logger, s.cfg.Engine, s.cfg.Store)
	papers := handlers.NewPaperHandler(s.cfg.Logger, s.cfg.Engine, s.cfg.Store)
	users := handlers.NewUserHandler(s.cfg.Logger, s.cfg.Store)
	auth := handlers.NewAuthHandler(s.cfg.Logger, s.cfg.Store)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", health.Get)
	mux.Handle("GET /metrics", promhttp.Handler())

	mux.HandleFunc("OPTIONS /v1/auth/register", middleware.PreflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("POST /v1/auth/register", auth.Register)
	mux.HandleFunc("OPTIONS /v1/auth/login", middleware.PreflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("POST /v1/auth/login", auth.Login)

	mux.HandleFunc("OPTIONS /v1/chat", middleware.PreflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("POST /v1/chat", chat.Post)
	mux.HandleFunc("GET /v1/chat/{id}", chat.GetMessages)

	mux.HandleFunc("OPTIONS /v1/papers", middleware.PreflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("GET /v1/papers", papers.SearchPapers)
	mux.HandleFunc("POST /v1/papers", papers.UploadPaper)
	mux.HandleFunc("OPTIONS /v1/papers/{id}", middleware.PreflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("GET /v1/papers/{id}", papers.GetPaper)
	mux.HandleFunc("PUT /v1/papers/{id}/metadata", papers.PutMetadata)
	mux.HandleFunc("DELETE /v1/papers/{id}", papers.DeletePaper)

	// Fetch PDF via S3 Pre-signed URL redirect
	mux.HandleFunc("GET /pdfs/{filename}", papers.GetPaperURL)

	mux.HandleFunc("OPTIONS /v1/users", middleware.PreflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("PUT /v1/users", users.PutUser)
	mux.HandleFunc("OPTIONS /v1/users/{id}/history", middleware.PreflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("GET /v1/users/{id}/history", users.GetHistory)
	mux.HandleFunc("DELETE /v1/users/{id}/chats/{conversation_id}", users.DeleteChat)

	return middleware.Chain(
		mux,
		middleware.Recover(s.cfg.Logger),
		middleware.RequestLog(s.cfg.Logger),
		middleware.Prometheus(),
		middleware.Auth(s.cfg.Logger),
		middleware.RateLimit(s.cfg.Logger),
		middleware.CORS(s.cfg.UIOrigin),
	)
}
