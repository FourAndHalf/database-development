package util

import (
	"crypto/rand"
	"encoding/hex"
)

// NewID returns a random 16-byte hex string (32 chars).
func NewID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	return hex.EncodeToString(b[:])
}

// TruncateTitle truncates a string to a given length, appending an ellipsis if needed.
func TruncateTitle(s string, max int) string {
	if len(s) > max {
		return s[:max] + "..."
	}
	return s
}
