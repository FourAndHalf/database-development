package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

type contextKey string

const UserIDKey contextKey = "user_id"

type Store struct {
	db *sql.DB
}

func New(connStr string) (*Store, error) {
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, err
	}

	// Set connection pool limits
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	if err := db.Ping(); err != nil {
		return nil, err
	}

	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		return nil, err
	}

	return s, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) migrate() error {
	// The users & papers schema is owned by scripts/schema.sql (canonical).
	// migrate() only ensures the legacy chat tables still used by the
	// not-yet-migrated chat flow; these are removed in the chat->requests slice.
	query := `
	CREATE TABLE IF NOT EXISTS conversations (
		id UUID PRIMARY KEY,
		user_id UUID REFERENCES users(id) ON DELETE CASCADE,
		title TEXT NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS messages (
		id UUID PRIMARY KEY,
		conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
		role TEXT NOT NULL,
		text TEXT NOT NULL,
		sources JSONB,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
		);

	ALTER TABLE messages ADD COLUMN IF NOT EXISTS sources JSONB;

		CREATE TABLE IF NOT EXISTS papers (
		id UUID PRIMARY KEY,
		title TEXT NOT NULL,
		filename TEXT UNIQUE NOT NULL,
		url TEXT,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS authors (
		id UUID PRIMARY KEY,
		name TEXT NOT NULL UNIQUE
	);

	CREATE TABLE IF NOT EXISTS paper_authors (
		paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
		author_id UUID REFERENCES authors(id) ON DELETE CASCADE,
		PRIMARY KEY (paper_id, author_id)
	);

	CREATE TABLE IF NOT EXISTS paper_metadata (
		paper_id UUID PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
		data JSONB NOT NULL DEFAULT '{}'::jsonb,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS daily_metrics (
		id SERIAL PRIMARY KEY,
		metric_date DATE NOT NULL UNIQUE,
		total_queries INTEGER NOT NULL DEFAULT 0,
		successful_queries INTEGER NOT NULL DEFAULT 0,
		failed_queries INTEGER NOT NULL DEFAULT 0,
		failure_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
		p50_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
		p95_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
		p99_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
		avg_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
		min_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
		max_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS query_latency_log (
		id SERIAL PRIMARY KEY,
		query_date DATE NOT NULL DEFAULT CURRENT_DATE,
		latency_ms NUMERIC(10,2) NOT NULL,
		success BOOLEAN NOT NULL DEFAULT true,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);
	CREATE INDEX IF NOT EXISTS idx_latency_log_date ON query_latency_log(query_date);

	INSERT INTO users (id, email, username, password_hash, is_admin)
	VALUES ('00000000-0000-0000-0000-000000000000', 'recruiter@aether.local', 'RECRUITER', 'nopass', false)
	ON CONFLICT (id) DO NOTHING;
	`
	_, err := s.db.Exec(query)
	return err
}

func (s *Store) EnsureConversation(ctx context.Context, id, userID, title string) error {
	var userVal interface{}
	if userID != "" && userID != "00000000-0000-0000-0000-000000000000" {
		userVal = userID
	} else {
		userVal = nil
	}

	query := `INSERT INTO conversations (id, user_id, title) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING`
	_, err := s.db.ExecContext(ctx, query, id, userVal, title)
	if err != nil {
		return fmt.Errorf("failed to ensure conversation: %w", err)
	}
	return nil
}

// SaveMessage persists a message. sourcesJSON is the pre-marshaled JSON array
// of sources for that message, or nil if the message has none.
func (s *Store) SaveMessage(ctx context.Context, conversationID, role, text string, sourcesJSON []byte) error {
	id := uuid.New().String()

	var sourcesVal interface{}
	if len(sourcesJSON) > 0 {
		sourcesVal = sourcesJSON
	}

	query := `INSERT INTO messages (id, conversation_id, role, text, sources) VALUES ($1, $2, $3, $4, $5)`
	_, err := s.db.ExecContext(ctx, query, id, conversationID, role, text, sourcesVal)
	if err != nil {
		return fmt.Errorf("failed to save message: %w", err)
	}
	return nil
}

func (s *Store) GetConversationMessages(ctx context.Context, conversationID string) ([]Message, error) {
	query := `
		SELECT id, conversation_id, role, text, sources, created_at
		FROM messages
		WHERE conversation_id = $1
		ORDER BY created_at ASC
	`
	rows, err := s.db.QueryContext(ctx, query, conversationID)
	if err != nil {
		return nil, fmt.Errorf("failed to get messages: %w", err)
	}
	defer rows.Close()

	var msgs []Message
	for rows.Next() {
		var m Message
		var sourcesJSON []byte
		if err := rows.Scan(&m.ID, &m.ConversationID, &m.Role, &m.Text, &sourcesJSON, &m.CreatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan message: %w", err)
		}
		if sourcesJSON != nil {
			m.Sources = json.RawMessage(sourcesJSON)
		}
		msgs = append(msgs, m)
	}
	return msgs, nil
}

func (s *Store) ConversationExists(ctx context.Context, conversationID string) (bool, error) {
	query := `SELECT EXISTS(SELECT 1 FROM conversations WHERE id = $1)`
	var exists bool
	if err := s.db.QueryRowContext(ctx, query, conversationID).Scan(&exists); err != nil {
		return false, fmt.Errorf("failed to check conversation existence: %w", err)
	}
	return exists, nil
}

func (s *Store) RecordQueryMetric(ctx context.Context, latencyMs int64, success bool) error {
	now := time.Now().UTC()
	dateStr := now.Format("2006-01-02")

	// Insert into query_latency_log
	logQuery := `INSERT INTO query_latency_log (query_date, latency_ms, success) VALUES ($1, $2, $3)`
	_, err := s.db.ExecContext(ctx, logQuery, dateStr, latencyMs, success)
	if err != nil {
		return fmt.Errorf("failed to log latency: %w", err)
	}

	// Upsert daily_metrics counters
	upsertQuery := `
		INSERT INTO daily_metrics (metric_date, total_queries, successful_queries, failed_queries, failure_rate)
		VALUES ($1, 1, CASE WHEN $2::boolean THEN 1 ELSE 0 END, CASE WHEN $2::boolean THEN 0 ELSE 1 END, CASE WHEN $2::boolean THEN 0 ELSE 100 END)
		ON CONFLICT (metric_date) DO UPDATE SET
			total_queries = daily_metrics.total_queries + 1,
			successful_queries = daily_metrics.successful_queries + CASE WHEN $2::boolean THEN 1 ELSE 0 END,
			failed_queries = daily_metrics.failed_queries + CASE WHEN $2::boolean THEN 0 ELSE 1 END,
			failure_rate = ROUND(((daily_metrics.failed_queries + CASE WHEN $2::boolean THEN 0 ELSE 1 END)::NUMERIC / (daily_metrics.total_queries + 1)) * 100, 2),
			updated_at = CURRENT_TIMESTAMP;
	`
	_, err = s.db.ExecContext(ctx, upsertQuery, dateStr, success)
	if err != nil {
		return fmt.Errorf("failed to upsert counters: %w", err)
	}

	// Update latency percentiles
	updateStatsQuery := `
		WITH stats AS (
			SELECT
				PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms) AS p50,
				PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95,
				PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99,
				AVG(latency_ms) AS avg_lat,
				MIN(latency_ms) AS min_lat,
				MAX(latency_ms) AS max_lat
			FROM query_latency_log
			WHERE query_date = $1
		)
		UPDATE daily_metrics SET
			p50_latency_ms = COALESCE(stats.p50, 0),
			p95_latency_ms = COALESCE(stats.p95, 0),
			p99_latency_ms = COALESCE(stats.p99, 0),
			avg_latency_ms = COALESCE(stats.avg_lat, 0),
			min_latency_ms = COALESCE(stats.min_lat, 0),
			max_latency_ms = COALESCE(stats.max_lat, 0),
			updated_at = CURRENT_TIMESTAMP
		FROM stats
		WHERE metric_date = $1;
	`
	_, err = s.db.ExecContext(ctx, updateStatsQuery, dateStr)
	if err != nil {
		return fmt.Errorf("failed to update percentiles: %w", err)
	}

	return nil
}

func (s *Store) GetDailyMetrics(ctx context.Context, days int) ([]DailyMetric, error) {
	query := `
		SELECT
			id, metric_date, total_queries, successful_queries, failed_queries, failure_rate,
			p50_latency_ms, p95_latency_ms, p99_latency_ms, avg_latency_ms, min_latency_ms, max_latency_ms,
			created_at, updated_at
		FROM daily_metrics
		ORDER BY metric_date DESC
		LIMIT $1
	`
	rows, err := s.db.QueryContext(ctx, query, days)
	if err != nil {
		return nil, fmt.Errorf("failed to get daily metrics: %w", err)
	}
	defer rows.Close()

	var metrics []DailyMetric
	for rows.Next() {
		var m DailyMetric
		var metricDate time.Time
		if err := rows.Scan(
			&m.ID, &metricDate, &m.TotalQueries, &m.SuccessfulQueries, &m.FailedQueries, &m.FailureRate,
			&m.P50LatencyMs, &m.P95LatencyMs, &m.P99LatencyMs, &m.AvgLatencyMs, &m.MinLatencyMs, &m.MaxLatencyMs,
			&m.CreatedAt, &m.UpdatedAt,
		); err != nil {
			return nil, fmt.Errorf("failed to scan metric: %w", err)
		}
		m.MetricDate = metricDate.Format("2006-01-02")
		metrics = append(metrics, m)
	}
	return metrics, nil
}

func (s *Store) GetTodayMetrics(ctx context.Context) (*DailyMetric, error) {
	now := time.Now().UTC()
	dateStr := now.Format("2006-01-02")

	query := `
		SELECT
			id, metric_date, total_queries, successful_queries, failed_queries, failure_rate,
			p50_latency_ms, p95_latency_ms, p99_latency_ms, avg_latency_ms, min_latency_ms, max_latency_ms,
			created_at, updated_at
		FROM daily_metrics
		WHERE metric_date = $1
	`
	row := s.db.QueryRowContext(ctx, query, dateStr)

	var m DailyMetric
	var metricDate time.Time
	if err := row.Scan(
		&m.ID, &metricDate, &m.TotalQueries, &m.SuccessfulQueries, &m.FailedQueries, &m.FailureRate,
		&m.P50LatencyMs, &m.P95LatencyMs, &m.P99LatencyMs, &m.AvgLatencyMs, &m.MinLatencyMs, &m.MaxLatencyMs,
		&m.CreatedAt, &m.UpdatedAt,
	); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to scan today metric: %w", err)
	}
	m.MetricDate = metricDate.Format("2006-01-02")
	return &m, nil
}
