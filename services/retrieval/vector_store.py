import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
import chromadb
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

class QdrantVectorStore(VectorStore):
    def __init__(self, host: str, port: int, collection_name: str, vector_size: int = 384):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size
        
        # Ensure collection exists
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
        except Exception as e:
            print(f"Error connecting to Qdrant: {e}")
            exists = False
        
        if not exists:
            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
                )
            except Exception as e:
                print(f"Failed to create Qdrant collection: {e}")

    def add(self, ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[Dict[str, Any]]):
        points = [
            models.PointStruct(
                id=i,
                vector=emb,
                payload={**meta, "page_content": doc}
            )
            for i, emb, doc, meta in zip(ids, embeddings, documents, metadatas)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def query(self, query_embeddings: List[List[float]], n_results: int) -> Dict[str, Any]:
        results = []
        for emb in query_embeddings:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=emb,
                limit=n_results
            )
            results.append(search_result)
        
        # Format to match ChromaDB style for compatibility
        formatted = {
            "documents": [[res.payload["page_content"] for res in results[0]]],
            "metadatas": [[{k: v for k, v in res.payload.items() if k != "page_content"} for res in results[0]]],
            "distances": [[1 - res.score for res in results[0]]] # Convert cosine similarity to distance
        }
        return formatted

    def delete(self, filename: str):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="source",
                        match=models.MatchValue(value=filename),
                    ),
                ]
            ),
        )

    def count(self) -> int:
        return self.client.get_collection(collection_name=self.collection_name).points_count

def get_vector_store() -> VectorStore:
    backend = os.getenv("VECTOR_BACKEND", "chroma").lower()
    collection_name = "database_papers"
    
    if backend == "qdrant":
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", 6333))
        # BGE-small-en-v1.5 has 384 dimensions
        return QdrantVectorStore(host=host, port=port, collection_name=collection_name, vector_size=384)
    else:
        path = os.getenv("CHROMA_DB_PATH", "data/chromadb")
        return ChromaVectorStore(path=path, collection_name=collection_name)
