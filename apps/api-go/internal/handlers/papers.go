package handlers

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"

	"database-development/apps/api-go/internal/rag"
	"database-development/apps/api-go/internal/store"
)

type PaperHandler struct {
	logger *log.Logger
	engine rag.Engine
	store  *store.Store
	s3     *s3.Client
	bucket    string
	s3Prefix  string
}

func NewPaperHandler(logger *log.Logger, engine rag.Engine, s *store.Store) *PaperHandler {
	// Initialize S3 client
	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		logger.Printf("Warning: failed to load AWS config for S3: %v", err)
	}

	bucket := os.Getenv("AWS_S3_BUCKET_NAME")
	if bucket == "" {
		logger.Printf("Warning: AWS_S3_BUCKET_NAME not set")
	}

	s3Prefix := os.Getenv("S3_RAW_PDFS_PREFIX")
	if s3Prefix == "" {
		s3Prefix = "raw_pdfs/"
	}

	return &PaperHandler{
		logger:    logger,
		engine:    engine,
		store:     s,
		s3:        s3.NewFromConfig(cfg),
		bucket:    bucket,
		s3Prefix:  s3Prefix,
	}
}

func (h *PaperHandler) GetPaper(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	id := r.PathValue("id")
	if id == "" {
		writeErr(w, http.StatusBadRequest, "missing_paper_id")
		return
	}

	pd, err := h.store.GetPaperWithMetadata(ctx, id)
	if err != nil {
		h.logger.Printf("Failed to get paper %s: %v", id, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	if pd == nil {
		writeErr(w, http.StatusNotFound, "paper_not_found")
		return
	}

	writeJSON(w, http.StatusOK, pd)
}

func (h *PaperHandler) PutMetadata(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	id := r.PathValue("id")
	if id == "" {
		writeErr(w, http.StatusBadRequest, "missing_paper_id")
		return
	}

	var metadata map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&metadata); err != nil {
		h.logger.Printf("Failed to decode metadata for paper %s: %v", id, err)
		writeErr(w, http.StatusBadRequest, "invalid_json")
		return
	}

	if err := h.store.UpdateMetadata(ctx, id, metadata); err != nil {
		h.logger.Printf("Failed to update metadata for paper %s: %v", id, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "updated"})
}

func (h *PaperHandler) SearchPapers(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	query := r.URL.Query().Get("q")
	page, _ := strconv.Atoi(r.URL.Query().Get("page"))
	if page < 1 {
		page = 1
	}
	pageSize, _ := strconv.Atoi(r.URL.Query().Get("pageSize"))
	if pageSize < 1 {
		pageSize = 10
	}

	paginatedResult, err := h.store.SearchPapers(ctx, query, page, pageSize)
	if err != nil {
		h.logger.Printf("Failed to search papers: %v", err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, paginatedResult)
}

func (h *PaperHandler) GetPaperURL(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	filename := r.PathValue("filename")
	if filename == "" {
		writeErr(w, http.StatusBadRequest, "missing_filename")
		return
	}

	if h.bucket == "" {
		h.logger.Printf("Cannot generate URL: AWS_S3_BUCKET_NAME not set")
		writeErr(w, http.StatusInternalServerError, "s3_not_configured")
		return
	}

	s3Key := h.s3Prefix + filepath.Base(filename)

	presignClient := s3.NewPresignClient(h.s3)
	req, err := presignClient.PresignGetObject(ctx, &s3.GetObjectInput{
		Bucket:                     aws.String(h.bucket),
		Key:                        aws.String(s3Key),
		ResponseContentType:        aws.String("application/pdf"),
		ResponseContentDisposition: aws.String("inline; filename=\"" + filename + "\""),
	}, func(opts *s3.PresignOptions) {
		opts.Expires = 15 * time.Minute
	})

	if err != nil {
		h.logger.Printf("Failed to generate presigned URL for %s: %v", s3Key, err)
		writeErr(w, http.StatusInternalServerError, "s3_presign_error")
		return
	}

	// We return a 302 Redirect to send the user's browser directly to the S3 URL
	http.Redirect(w, r, req.URL, http.StatusFound)
}
