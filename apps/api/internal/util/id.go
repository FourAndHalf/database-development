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

