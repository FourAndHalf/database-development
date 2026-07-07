package handlers

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"log"
	"net/http"
	"net/smtp"
	"os"
	"strings"
	"time"

	"database-development/apps/api-go/internal/util"
)

type BugHandler struct {
	logger *log.Logger
}

func NewBugHandler(logger *log.Logger) *BugHandler {
	return &BugHandler{logger: logger}
}

func (h *BugHandler) ReportBug(w http.ResponseWriter, r *http.Request) {
	err := r.ParseMultipartForm(50 << 20) // 50MB
	if err != nil {
		writeErr(w, http.StatusBadRequest, "invalid_form")
		return
	}

	description := r.FormValue("description")
	ccEmail := r.FormValue("ccEmail")
	screenshotBase64 := r.FormValue("screenshot") // Base64 data URI

	// Create email
	to := []string{"jinsoneb@gmail.com"}
	if ccEmail != "" {
		to = append(to, ccEmail)
	}

	// We'll use a dummy/simple SMTP sending, assuming standard env vars or standard Go
	smtpHost := os.Getenv("SMTP_HOST")
	smtpPort := os.Getenv("SMTP_PORT")
	smtpUser := os.Getenv("SMTP_USER")
	smtpPass := os.Getenv("SMTP_PASS")
	fromEmail := os.Getenv("SMTP_FROM")

	if smtpHost == "" {
		// Mock sending if not configured
		h.logger.Printf("Mock Bug Report:\nDesc: %s\nCC: %s\nImages attached.", description, ccEmail)
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}

	if fromEmail == "" {
		fromEmail = "noreply@example.com" // fallback
	}

	// Create a multipart email
	boundary := "aether-bug-boundary-" + util.NewID()
	var body bytes.Buffer

	body.WriteString(fmt.Sprintf("From: %s\r\n", fromEmail))
	body.WriteString(fmt.Sprintf("To: %s\r\n", strings.Join(to, ",")))
	body.WriteString("Subject: Bug Report - Aether UI\r\n")
	body.WriteString("MIME-Version: 1.0\r\n")
	body.WriteString(fmt.Sprintf("Content-Type: multipart/mixed; boundary=%s\r\n", boundary))
	body.WriteString("\r\n")

	// Text part
	body.WriteString(fmt.Sprintf("--%s\r\n", boundary))
	body.WriteString("Content-Type: text/plain; charset=utf-8\r\n")
	body.WriteString("\r\n")
	body.WriteString(fmt.Sprintf("Bug Description:\n%s\n\nReported at: %s\n", description, time.Now().Format(time.RFC3339)))
	body.WriteString("\r\n")

	// Screenshot (if any)
	if strings.HasPrefix(screenshotBase64, "data:image") {
		parts := strings.SplitN(screenshotBase64, ",", 2)
		if len(parts) == 2 {
			imgType := "png"
			if strings.Contains(parts[0], "jpeg") {
				imgType = "jpeg"
			}
			body.WriteString(fmt.Sprintf("--%s\r\n", boundary))
			body.WriteString(fmt.Sprintf("Content-Type: image/%s\r\n", imgType))
			body.WriteString("Content-Transfer-Encoding: base64\r\n")
			body.WriteString(fmt.Sprintf("Content-Disposition: attachment; filename=\"screenshot.%s\"\r\n", imgType))
			body.WriteString("\r\n")
			body.WriteString(parts[1])
			body.WriteString("\r\n")
		}
	}

	// Extra images
	if r.MultipartForm != nil && r.MultipartForm.File != nil {
		for _, files := range r.MultipartForm.File {
			for _, fileHeader := range files {
				if !strings.HasPrefix(fileHeader.Filename, "extra-") {
					continue
				}
			file, err := fileHeader.Open()
			if err != nil {
				continue
			}
			defer file.Close()
			buf := new(bytes.Buffer)
			buf.ReadFrom(file)
			encoded := base64.StdEncoding.EncodeToString(buf.Bytes())
			
			body.WriteString(fmt.Sprintf("--%s\r\n", boundary))
			body.WriteString(fmt.Sprintf("Content-Type: %s\r\n", fileHeader.Header.Get("Content-Type")))
			body.WriteString("Content-Transfer-Encoding: base64\r\n")
			body.WriteString(fmt.Sprintf("Content-Disposition: attachment; filename=\"%s\"\r\n", fileHeader.Filename))
			body.WriteString("\r\n")
			chunked := chunkString(encoded, 76)
			body.WriteString(chunked)
			body.WriteString("\r\n")
			}
		}
	}
	body.WriteString(fmt.Sprintf("--%s--\r\n", boundary))

	auth := smtp.PlainAuth("", smtpUser, smtpPass, smtpHost)
	err = smtp.SendMail(fmt.Sprintf("%s:%s", smtpHost, smtpPort), auth, fromEmail, to, body.Bytes())
	if err != nil {
		h.logger.Printf("Failed to send bug report email: %v", err)
		writeErr(w, http.StatusInternalServerError, "email_failed")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func chunkString(s string, chunkSize int) string {
	var chunks []string
	runes := []rune(s)
	for i := 0; i < len(runes); i += chunkSize {
		end := i + chunkSize
		if end > len(runes) {
			end = len(runes)
		}
		chunks = append(chunks, string(runes[i:end]))
	}
	return strings.Join(chunks, "\r\n")
}
