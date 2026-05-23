package middleware

import (
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

type client struct {
	limiter  *rate.Limiter
	lastSeen time.Time
}

func RateLimit(logger *log.Logger) Middleware {
	var (
		mu      sync.Mutex
		clients = make(map[string]*client)
	)

	// Clean up old clients every minute
	go func() {
		for {
			time.Sleep(time.Minute)
			mu.Lock()
			for ip, c := range clients {
				if time.Since(c.lastSeen) > 3*time.Minute {
					delete(clients, ip)
				}
			}
			mu.Unlock()
		}
	}()

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			ip := strings.Split(r.RemoteAddr, ":")[0]

			mu.Lock()
			if _, found := clients[ip]; !found {
				// 5 requests per second burst of 10
				clients[ip] = &client{limiter: rate.NewLimiter(5, 10)}
			}
			clients[ip].lastSeen = time.Now()
			if !clients[ip].limiter.Allow() {
				mu.Unlock()
				logger.Printf("Rate limit exceeded for IP: %s", ip)
				writeJSON(w, http.StatusTooManyRequests, map[string]any{
					"error": "too_many_requests",
				})
				return
			}
			mu.Unlock()

			next.ServeHTTP(w, r)
		})
	}
}
