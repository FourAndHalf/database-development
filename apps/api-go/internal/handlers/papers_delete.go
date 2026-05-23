package handlers

import (
	"net/http"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/s3"

	"database-development/apps/api-go/internal/store"
)

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

	// 4. Delete from S3
	if h.bucket != "" {
		s3Key := h.s3Prefix + filename
		_, err = h.s3.DeleteObject(ctx, &s3.DeleteObjectInput{
			Bucket: aws.String(h.bucket),
			Key:    aws.String(s3Key),
		})
		if err != nil {
			h.logger.Printf("Warning: failed to delete %s from S3: %v", filename, err)
			// Non-fatal error, still return success
		}
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "deleted", "filename": filename})
}
