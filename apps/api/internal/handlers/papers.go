package handlers

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"database-development/apps/api/internal/rag"
	"database-development/apps/api/internal/store"
)

type PaperHandler struct {
	logger *log.Logger
	engine rag.Engine
	store  *store.Store
}

func NewPaperHandler(logger *log.Logger, engine rag.Engine, s *store.Store) *PaperHandler {
	return &PaperHandler{logger: logger, engine: engine, store: s}
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

func (h *PaperHandler) DeletePaper(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	id := r.PathValue("id")
	if id == "" {
		writeErr(w, http.StatusBadRequest, "missing_paper_id")
		return
	}

	// 1. Authorization Check (Admin only)
	userID, ok := ctx.Value(store.UserIDKey).(string)
	if !ok || userID == "" {
		writeErr(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	user, err := h.store.GetUserByID(ctx, userID)
	if err != nil || user == nil || user.TypeID != 2 {
		writeErr(w, http.StatusForbidden, "forbidden_admin_only")
		return
	}

	// 2. Delete from PostgreSQL and get filename
	filename, err := h.store.DeletePaper(ctx, id)
	if err != nil {
		h.logger.Printf("Failed to delete paper %s from DB: %v", id, err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}
	if filename == "" {
		writeErr(w, http.StatusNotFound, "paper_not_found")
		return
	}

	// 3. Delete from Vector DB (Chroma via Python Engine)
	err = h.engine.DeleteDocument(ctx, filename)
	if err != nil {
		h.logger.Printf("Failed to delete vectors for %s: %v", filename, err)
		writeErr(w, http.StatusInternalServerError, "vector_db_deletion_failed")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "deleted", "filename": filename})
}

func (h *PaperHandler) UploadPaper(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	// 1. Admin check
	userID, ok := ctx.Value(store.UserIDKey).(string)
	if !ok || userID == "" {
		writeErr(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	user, err := h.store.GetUserByID(ctx, userID)
	if err != nil || user == nil || user.TypeID != 2 {
		writeErr(w, http.StatusForbidden, "forbidden_admin_only")
		return
	}

	// 2. Parse Multipart Form (10 MB max memory)
	if err := r.ParseMultipartForm(10 << 20); err != nil {
		h.logger.Printf("Failed to parse multipart form: %v", err)
		writeErr(w, http.StatusBadRequest, "invalid_form")
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "missing_file")
		return
	}
	defer file.Close()

	if strings.ToLower(filepath.Ext(header.Filename)) != ".pdf" {
		writeErr(w, http.StatusBadRequest, "invalid_file_type_only_pdf_allowed")
		return
	}

	title := r.FormValue("title")
	if title == "" {
		title = header.Filename
	}

	// 3. Save file to data/raw_pdfs/
	dataPath := "../../data"
	if envDataPath := os.Getenv("DATA_DIR"); envDataPath != "" {
		dataPath = envDataPath
	}
	pdfDir := filepath.Join(dataPath, "raw_pdfs")
	if err := os.MkdirAll(pdfDir, 0755); err != nil {
		h.logger.Printf("Failed to create pdf directory: %v", err)
		writeErr(w, http.StatusInternalServerError, "io_error")
		return
	}

	filename := header.Filename
	// Clean filename to avoid path traversal
	filename = filepath.Base(filename)
	destPath := filepath.Join(pdfDir, filename)

	destFile, err := os.Create(destPath)
	if err != nil {
		h.logger.Printf("Failed to create dest file %s: %v", destPath, err)
		writeErr(w, http.StatusInternalServerError, "io_error")
		return
	}
	defer destFile.Close()

	if _, err := io.Copy(destFile, file); err != nil {
		h.logger.Printf("Failed to copy file content: %v", err)
		writeErr(w, http.StatusInternalServerError, "io_error")
		return
	}

	// 4. Save to Database
	p := &store.Paper{
		Title:    title,
		Filename: filename,
	}
	paperID, err := h.store.SavePaper(ctx, p)
	if err != nil {
		h.logger.Printf("Failed to save paper to DB: %v", err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	// 5. Process Authors
	authorsStr := r.FormValue("authors")
	if authorsStr != "" {
		authorNames := strings.Split(authorsStr, ",")
		for _, name := range authorNames {
			name = strings.TrimSpace(name)
			if name == "" {
				continue
			}
			authorID, err := h.store.UpsertAuthor(ctx, name)
			if err == nil {
				_ = h.store.LinkAuthorToPaper(ctx, paperID, authorID)
			}
		}
	}

	// 6. Process Tags metadata
	tagsStr := r.FormValue("tags")
	if tagsStr != "" {
		tags := strings.Split(tagsStr, ",")
		for i := range tags {
			tags[i] = strings.TrimSpace(tags[i])
		}
		metadata := map[string]interface{}{"tags": tags}
		_ = h.store.UpdateMetadata(ctx, paperID, metadata)
	}

	writeJSON(w, http.StatusCreated, map[string]string{
		"status":  "success",
		"id":      paperID,
		"message": "Paper uploaded and saved to DB. Note: It still needs to be chunked and vectorized via Python to be searchable in chat.",
	})
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

	papers, err := h.store.SearchPapers(ctx, query)
	if err != nil {
		h.logger.Printf("Failed to search papers: %v", err)
		writeErr(w, http.StatusInternalServerError, "db_error")
		return
	}

	writeJSON(w, http.StatusOK, papers)
}
