import os
import sys
import json
import uuid
import psycopg2
import boto3
from pathlib import Path
from tqdm import tqdm
from psycopg2.extras import RealDictCursor, Json
from docling.document_converter import DocumentConverter
from dotenv import load_dotenv

# Add the project root to sys.path to allow importing services
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from services.ingestion.pdf_parser import PdfParser
from services.ingestion.vectorize import Vectorizer

load_dotenv()

# --- Configuration ---
DB_URL = os.getenv("DB_URL", "postgres://nexus:PinkFloyd@localhost:5435/nexus_db")
S3_BUCKET = os.getenv("AWS_S3_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_RAW_PDFS_PREFIX", "raw_pdfs/")
LOCAL_PARSED_DIR = Path(os.getenv("LOCAL_PARSED_DIR", "data/parsed"))

def get_db_connection():
    return psycopg2.connect(DB_URL)

def list_s3_pdfs(s3_client, bucket, prefix):
    """Lists all PDF files in the specified S3 bucket and prefix."""
    pdfs = []
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if key.lower().endswith('.pdf'):
                    pdfs.append(key)
    return pdfs

def repopulate():
    print(f"Starting repopulation from S3 bucket: {S3_BUCKET}")
    
    if not S3_BUCKET:
        print("Error: AWS_S3_BUCKET_NAME not set.")
        return

    s3_client = boto3.client('s3')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Initialize Parser and Vectorizer
    converter = DocumentConverter()
    pdf_parser = PdfParser(converter=converter, output_dir=LOCAL_PARSED_DIR)
    vectorizer = Vectorizer()

    # 1. List PDFs from S3
    s3_keys = list_s3_pdfs(s3_client, S3_BUCKET, S3_PREFIX)
    print(f"Found {len(s3_keys)} PDFs in S3.")

    for s3_key in tqdm(s3_keys, desc="Processing PDFs"):
        filename = os.path.basename(s3_key)
        
        # 2. Parse PDF (Handles S3 download and caching)
        print(f"\nProcessing: {filename}")
        doc = pdf_parser.parse_pdf(filename)
        if not doc:
            print(f"Failed to parse {filename}, skipping.")
            continue

        # 3. Vectorize and Store with deterministic UUIDs
        chunks = vectorizer.chunk_text(content)
        embeddings = vectorizer.embedder.embed_batch(chunks)

        # Generate deterministic UUIDs for each chunk to be Qdrant-compatible
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8') # DNS namespace
        ids = [str(uuid.uuid5(namespace, f"{filename}-{i}")) for i in range(len(chunks))]
        metadatas = [{"source": filename, "chunk_number": i} for i in range(len(chunks))]

        vectorizer.vector_store.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Stored {len(chunks)} vectors for {filename}")

        # 4. Ingest Metadata into Postgres
        paper_id = str(uuid.uuid4())
        title = data.get("name", filename.replace(".pdf", "").replace("_", " ").title())
        
        # Heuristic for authors and preview (from ingest_metadata.py)
        content_preview = content[:1000]
        authors = []
        texts = data.get("texts", [])
        for i, t in enumerate(texts[:10]):
            text_val = t.get("text", "").strip()
            if not text_val: continue
            if i > 0 and i < 5 and len(text_val) < 100 and ("," in text_val or " " in text_val):
                possible_authors = [a.strip() for a in text_val.replace(" and ", ",").split(",")]
                authors.extend([a for a in possible_authors if len(a) > 2])
        authors = list(set(authors))[:5]

        try:
            # Save Paper
            cur.execute("""
                INSERT INTO papers (id, title, filename)
                VALUES (%s, %s, %s)
                ON CONFLICT (filename) DO UPDATE SET title = EXCLUDED.title, updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (paper_id, title, filename))
            db_paper_id = cur.fetchone()['id']
            
            # Save Authors
            for author_name in authors:
                author_uuid = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO authors (id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                """, (author_uuid, author_name))
                db_author_id = cur.fetchone()['id']
                
                cur.execute("""
                    INSERT INTO paper_authors (paper_id, author_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (db_paper_id, db_author_id))
            
            # Save Metadata
            metadata = {
                "abstract_snippet": content_preview + "...",
                "source_format": "Docling JSON",
                "repopulated_at": "2026-05-29"
            }
            cur.execute("""
                INSERT INTO paper_metadata (paper_id, data)
                VALUES (%s, %s)
                ON CONFLICT (paper_id) DO UPDATE SET data = paper_metadata.data || EXCLUDED.data
            """, (db_paper_id, Json(metadata)))
            
            conn.commit()
            print(f"Metadata ingested for {filename}")
        except Exception as e:
            print(f"Error ingesting metadata for {filename}: {e}")
            conn.rollback()

    cur.close()
    conn.close()
    print("\nRepopulation complete!")

if __name__ == "__main__":
    repopulate()
