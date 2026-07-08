"""
One-time migration: copy every chunk out of the existing ChromaDB collection
and into the Postgres `chunks` table (pgvector). Run once per environment,
after applying scripts/schema.sql and before flipping VECTOR_BACKEND=pgvector.

Usage:
    python3 scripts/migrate_chroma_to_pgvector.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import chromadb
import psycopg2
from psycopg2.extras import execute_values
from pgvector import Vector
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 500


def main():
    chroma_path = os.getenv("CHROMA_DB_PATH", "data/chromadb")
    dsn = os.environ["DATABASE_URL"]

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(name="database_papers")
    total = collection.count()
    print(f"Source collection has {total} chunks.")
    if total == 0:
        print("Nothing to migrate.")
        return

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    register_vector(conn)

    migrated = 0
    offset = 0
    with conn.cursor() as cur:
        while offset < total:
            batch = collection.get(
                limit=BATCH_SIZE,
                offset=offset,
                include=["embeddings", "documents", "metadatas"],
            )
            rows = [
                (
                    batch["ids"][i],
                    Vector(batch["embeddings"][i]),
                    batch["documents"][i],
                    batch["metadatas"][i].get("source", ""),
                    batch["metadatas"][i].get("section", ""),
                    batch["metadatas"][i].get("subsection", ""),
                    batch["metadatas"][i].get("concepts", ""),
                )
                for i in range(len(batch["ids"]))
            ]
            execute_values(
                cur,
                """
                INSERT INTO chunks (id, embedding, content, source, section, subsection, concepts)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    content = EXCLUDED.content,
                    source = EXCLUDED.source,
                    section = EXCLUDED.section,
                    subsection = EXCLUDED.subsection,
                    concepts = EXCLUDED.concepts
                """,
                rows,
            )
            migrated += len(rows)
            offset += BATCH_SIZE
            print(f"Migrated {migrated}/{total}...")

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks")
        pg_count = cur.fetchone()[0]

    print(f"\nDone. Chroma: {total} chunks -> Postgres chunks table: {pg_count} rows.")
    if pg_count != total:
        print("WARNING: counts don't match — investigate before cutting over.")


if __name__ == "__main__":
    main()
