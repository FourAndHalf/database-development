package httpserver

import (
	"log"
	"net/http"

	"database-development/apps/api/internal/handlers"
	"database-development/apps/api/internal/rag"
	"database-development/apps/api/internal/store"
	"github.com/prometheus/client_golang/prometheus/promhttp"
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
	return s.mux
}
func (s *Server) routes() http.Handler {
	health := handlers.NewHealthHandler()
	chat := handlers.NewChatHandler(s.cfg.Logger, s.cfg.Engine, s.cfg.Store)
	papers := handlers.NewPaperHandler(s.cfg.Logger, s.cfg.Store)
	users := handlers.NewUserHandler(s.cfg.Logger, s.cfg.Store)
	auth := handlers.NewAuthHandler(s.cfg.Logger, s.cfg.Store)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", health.Get)
	mux.Handle("GET /metrics", promhttp.Handler())

	mux.HandleFunc("OPTIONS /v1/auth/register", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("POST /v1/auth/register", auth.Register)
	mux.HandleFunc("OPTIONS /v1/auth/login", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("POST /v1/auth/login", auth.Login)

	mux.HandleFunc("OPTIONS /v1/chat", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("POST /v1/chat", chat.Post)
	mux.HandleFunc("GET /v1/chat/{id}", chat.GetConversation)

	mux.HandleFunc("OPTIONS /v1/papers", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("GET /v1/papers", papers.SearchPapers)
	mux.HandleFunc("OPTIONS /v1/papers/{id}", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("GET /v1/papers/{id}", papers.GetPaper)
	mux.HandleFunc("PUT /v1/papers/{id}/metadata", papers.PutMetadata)

	// Proxy PDFs to Python Service
	mux.HandleFunc("GET /pdfs/{filename}", func(w http.ResponseWriter, r *http.Request) {
		filename := r.PathValue("filename")
		http.Redirect(w, r, s.cfg.PythonServiceURL+"/pdfs/"+filename, http.StatusTemporaryRedirect)
	})

	mux.HandleFunc("OPTIONS /v1/users", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("PUT /v1/users", users.PutUser)
	mux.HandleFunc("OPTIONS /v1/users/{id}/history", preflightHandler(s.cfg.UIOrigin))
	mux.HandleFunc("GET /v1/users/{id}/history", users.GetHistory)
	mux.HandleFunc("DELETE /v1/users/{id}/chats/{conversation_id}", users.DeleteChat)

	return chain(
		mux,
		recoverMiddleware(s.cfg.Logger),
		requestLogMiddleware(s.cfg.Logger),
		prometheusMiddleware(),
		authMiddleware(s.cfg.Logger),
		rateLimitMiddleware(s.cfg.Logger),
		corsMiddleware(s.cfg.UIOrigin),
	)
}

