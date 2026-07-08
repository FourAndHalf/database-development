import os
from typing import List, Dict, Any
import chromadb
import psycopg2
from pgvector import Vector
from pgvector.psycopg2 import register_vector
from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    def add(self, ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def query(self, query_embeddings: List[List[float]], n_results: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete(self, filename: str):
        pass

    @abstractmethod
    def count(self) -> int:
        pass

class ChromaVectorStore(VectorStore):
    def __init__(self, path: str, collection_name: str):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add(self, ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[Dict[str, Any]]):
        self.collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query(self, query_embeddings: List[List[float]], n_results: int) -> Dict[str, Any]:
        return self.collection.query(query_embeddings=query_embeddings, n_results=n_results)

    def delete(self, filename: str):
        self.collection.delete(where={"source": filename})

    def count(self) -> int:
        return self.collection.count()

class PgVectorStore(VectorStore):
    def __init__(self, dsn: str):
        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True
        register_vector(self.conn)

    def add(self, ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[Dict[str, Any]]):
        rows = [
            (
                ids[i],
                Vector(embeddings[i]),
                documents[i],
                metadatas[i].get("source", ""),
                metadatas[i].get("section", ""),
                metadatas[i].get("subsection", ""),
                metadatas[i].get("concepts", ""),
            )
            for i in range(len(ids))
        ]
        with self.conn.cursor() as cur:
            from psycopg2.extras import execute_values
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

    def query(self, query_embeddings: List[List[float]], n_results: int) -> Dict[str, Any]:
        documents, metadatas, distances = [], [], []
        with self.conn.cursor() as cur:
            for embedding in query_embeddings:
                vec = Vector(embedding)
                cur.execute(
                    """
                    SELECT content, source, section, subsection, concepts, embedding <=> %s AS distance
                    FROM chunks
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (vec, vec, n_results),
                )
                rows = cur.fetchall()
                documents.append([r[0] for r in rows])
                metadatas.append([
                    {"source": r[1], "section": r[2], "subsection": r[3], "concepts": r[4]}
                    for r in rows
                ])
                distances.append([r[5] for r in rows])
        return {"documents": documents, "metadatas": metadatas, "distances": distances}

    def delete(self, filename: str):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE source = %s", (filename,))

    def count(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chunks")
            return cur.fetchone()[0]

def get_vector_store() -> VectorStore:
    backend = os.getenv("VECTOR_BACKEND", "chroma")
    if backend == "pgvector":
        dsn = os.environ["DATABASE_URL"]
        return PgVectorStore(dsn=dsn)

    collection_name = "database_papers"
    path = os.getenv("CHROMA_DB_PATH", "data/chromadb")
    return ChromaVectorStore(path=path, collection_name=collection_name)
