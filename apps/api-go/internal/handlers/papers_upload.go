package handlers

import (
	"net/http"
	"path/filepath"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/s3"

	"database-development/apps/api-go/internal/store"
)

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

	if h.bucket == "" {
		h.logger.Printf("Cannot upload paper: AWS_S3_BUCKET_NAME not set")
		writeErr(w, http.StatusInternalServerError, "s3_not_configured")
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

	filename := filepath.Base(header.Filename)
	s3Key := h.s3Prefix + filename

	// 3. Upload to S3
	_, err = h.s3.PutObject(ctx, &s3.PutObjectInput{
		Bucket: aws.String(h.bucket),
		Key:    aws.String(s3Key),
		Body:   file,
	})
	if err != nil {
		h.logger.Printf("Failed to upload to S3 (%s): %v", s3Key, err)
		writeErr(w, http.StatusInternalServerError, "s3_upload_failed")
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
		// Attempt to clean up the orphaned S3 object
		_, _ = h.s3.DeleteObject(ctx, &s3.DeleteObjectInput{
			Bucket: aws.String(h.bucket),
			Key:    aws.String(s3Key),
		})
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
		"message": "Paper uploaded securely to S3 and saved to DB. Note: It still needs to be chunked and vectorized via Python to be searchable in chat.",
	})
}
