package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
)

func (s *Store) SavePaper(ctx context.Context, p *Paper) (string, error) {
	if p.ID == "" {
		p.ID = uuid.New().String()
	}

	query := `
		INSERT INTO papers (id, title, filename, url)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (filename) DO UPDATE
		SET title = EXCLUDED.title, url = EXCLUDED.url, updated_at = CURRENT_TIMESTAMP
		RETURNING id
	`
	var id string
	err := s.db.QueryRowContext(ctx, query, p.ID, p.Title, p.Filename, p.URL).Scan(&id)
	if err != nil {
		return "", fmt.Errorf("failed to save paper: %w", err)
	}
	p.ID = id
	return id, nil
}

func (s *Store) UpsertAuthor(ctx context.Context, name string) (string, error) {
	id := uuid.New().String()
	query := `
		INSERT INTO authors (id, name)
		VALUES ($1, $2)
		ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
		RETURNING id
	`
	var actualID string
	err := s.db.QueryRowContext(ctx, query, id, name).Scan(&actualID)
	if err != nil {
		return "", fmt.Errorf("failed to upsert author: %w", err)
	}
	return actualID, nil
}

func (s *Store) LinkAuthorToPaper(ctx context.Context, paperID, authorID string) error {
	query := `
		INSERT INTO paper_authors (paper_id, author_id)
		VALUES ($1, $2)
		ON CONFLICT DO NOTHING
	`
	_, err := s.db.ExecContext(ctx, query, paperID, authorID)
	if err != nil {
		return fmt.Errorf("failed to link author to paper: %w", err)
	}
	return nil
}

func (s *Store) UpdateMetadata(ctx context.Context, paperID string, data map[string]interface{}) error {
	jsonData, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("failed to marshal metadata: %w", err)
	}

	query := `
		INSERT INTO paper_metadata (paper_id, data)
		VALUES ($1, $2)
		ON CONFLICT (paper_id) DO UPDATE
		SET data = paper_metadata.data || EXCLUDED.data, updated_at = CURRENT_TIMESTAMP
	`
	_, err = s.db.ExecContext(ctx, query, paperID, jsonData)
	if err != nil {
		return fmt.Errorf("failed to update paper metadata: %w", err)
	}
	return nil
}

func (s *Store) GetPaperWithMetadata(ctx context.Context, paperID string) (*PaperDetail, error) {
	paperQuery := `
		SELECT p.id, p.title, p.filename, COALESCE(p.url, '') as url, p.created_at, p.updated_at, m.data
		FROM papers p
		LEFT JOIN paper_metadata m ON p.id = m.paper_id
		WHERE p.id = $1
	`
	var pd PaperDetail
	var metadataJSON []byte
	err := s.db.QueryRowContext(ctx, paperQuery, paperID).Scan(
		&pd.ID, &pd.Title, &pd.Filename, &pd.URL, &pd.CreatedAt, &pd.UpdatedAt, &metadataJSON,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get paper: %w", err)
	}

	if metadataJSON != nil {
		if err := json.Unmarshal(metadataJSON, &pd.Metadata); err != nil {
			return nil, fmt.Errorf("failed to unmarshal metadata: %w", err)
		}
	} else {
		pd.Metadata = make(map[string]interface{})
	}

	authorQuery := `
		SELECT a.id, a.name
		FROM authors a
		JOIN paper_authors pa ON a.id = pa.author_id
		WHERE pa.paper_id = $1
	`
	rows, err := s.db.QueryContext(ctx, authorQuery, paperID)
	if err != nil {
		return nil, fmt.Errorf("failed to get paper authors: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var a Author
		if err := rows.Scan(&a.ID, &a.Name); err != nil {
			return nil, fmt.Errorf("failed to scan author: %w", err)
		}
		pd.Authors = append(pd.Authors, a)
	}

	return &pd, nil
}

func (s *Store) DeletePaper(ctx context.Context, id string) (string, error) {
	var filename string
	err := s.db.QueryRowContext(ctx, "DELETE FROM papers WHERE id = $1 RETURNING filename", id).Scan(&filename)
	if err != nil {
		if err == sql.ErrNoRows {
			return "", nil // Paper not found
		}
		return "", fmt.Errorf("failed to delete paper: %w", err)
	}
	return filename, nil
}

func (s *Store) SearchPapers(ctx context.Context, query string, page, pageSize int) (*PaginatedPapers, error) {
	offset := (page - 1) * pageSize
	sqlQuery := `
		SELECT
			p.id, p.title, p.filename, COALESCE(p.url, '') as url, p.created_at, p.updated_at,
			COALESCE(json_agg(json_build_object('id', a.id, 'name', a.name)) FILTER (WHERE a.id IS NOT NULL), '[]') as authors
		FROM papers p
		LEFT JOIN paper_authors pa ON p.id = pa.paper_id
		LEFT JOIN authors a ON pa.author_id = a.id
		WHERE p.title ILIKE $1 OR a.name ILIKE $1
		GROUP BY p.id
		ORDER BY p.title ASC
		LIMIT $2 OFFSET $3
	`
	rows, err := s.db.QueryContext(ctx, sqlQuery, "%"+query+"%", pageSize, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to search papers: %w", err)
	}
	defer rows.Close()

	var papers []PaperDetail
	for rows.Next() {
		var pd PaperDetail
		var authorsJSON []byte
		if err := rows.Scan(&pd.ID, &pd.Title, &pd.Filename, &pd.URL, &pd.CreatedAt, &pd.UpdatedAt, &authorsJSON); err != nil {
			return nil, fmt.Errorf("failed to scan paper: %w", err)
		}
		if err := json.Unmarshal(authorsJSON, &pd.Authors); err != nil {
			return nil, fmt.Errorf("failed to unmarshal authors: %w", err)
		}
		papers = append(papers, pd)
	}

	countQuery := `
		SELECT COUNT(DISTINCT p.id)
		FROM papers p
		LEFT JOIN paper_authors pa ON p.id = pa.paper_id
		LEFT JOIN authors a ON pa.author_id = a.id
		WHERE p.title ILIKE $1 OR a.name ILIKE $1
	`
	var total int
	if err := s.db.QueryRowContext(ctx, countQuery, "%"+query+"%").Scan(&total); err != nil {
		return nil, fmt.Errorf("failed to count papers: %w", err)
	}

	return &PaginatedPapers{
		Papers: papers,
		Total:  total,
	}, nil
}
