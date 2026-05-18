import os
import json
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor, Json

DB_URL = "postgres://nexus:password@localhost:5434/nexus_db"

def ingest_metadata():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    parsed_dir = "data/parsed"
    files = [f for f in os.listdir(parsed_dir) if f.endswith(".json")]
    
    print(f"Found {len(files)} files to ingest.")
    
    for filename in files:
        filepath = os.path.join(parsed_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        paper_id = str(uuid.uuid4())
        title = data.get("name", filename.replace(".json", "").replace("_", " ").title())
        orig_filename = data.get("origin", {}).get("filename", filename.replace(".json", ".pdf"))
        
        # Basic extraction logic for Docling structure
        texts = data.get("texts", [])
        content_preview = ""
        authors = []
        
        # Try to find authors and a bit of history (first few blocks)
        for i, t in enumerate(texts[:10]):
            text_val = t.get("text", "").strip()
            if not text_val: continue
            
            # Heuristic for authors: often comma separated or multiple small lines after title
            if i > 0 and i < 5 and len(text_val) < 100 and ("," in text_val or " " in text_val):
                possible_authors = [a.strip() for a in text_val.replace(" and ", ",").split(",")]
                authors.extend([a for a in possible_authors if len(a) > 2])
            
            if i < 8:
                content_preview += text_val + " "

        # Clean authors
        authors = list(set(authors))[:5] # Limit to 5
        
        print(f"Ingesting: {title}")
        
        try:
            # 1. Save Paper
            cur.execute("""
                INSERT INTO papers (id, title, filename)
                VALUES (%s, %s, %s)
                ON CONFLICT (filename) DO UPDATE SET title = EXCLUDED.title
                RETURNING id
            """, (paper_id, title, orig_filename))
            db_paper_id = cur.fetchone()['id']
            
            # 2. Save Authors and Link
            for author_name in authors:
                author_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO authors (id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                """, (author_id, author_name))
                db_author_id = cur.fetchone()['id']
                
                cur.execute("""
                    INSERT INTO paper_authors (paper_id, author_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (db_paper_id, db_author_id))
                
            # 3. Save Metadata (History & Context snippet)
            metadata = {
                "abstract_snippet": content_preview[:1000] + "...",
                "source_format": "Docling JSON",
                "ingested_at": "2026-05-18"
            }
            cur.execute("""
                INSERT INTO paper_metadata (paper_id, data)
                VALUES (%s, %s)
                ON CONFLICT (paper_id) DO UPDATE SET data = paper_metadata.data || EXCLUDED.data
            """, (db_paper_id, Json(metadata)))
            
        except Exception as e:
            print(f"Error ingesting {filename}: {e}")
            conn.rollback()
        else:
            conn.commit()
            
    cur.close()
    conn.close()
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_metadata()
