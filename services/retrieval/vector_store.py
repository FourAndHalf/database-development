import os
from typing import List, Dict, Any
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

def get_vector_store() -> VectorStore:
    collection_name = "database_papers"
    path = os.getenv("CHROMA_DB_PATH", "data/chromadb")
    return ChromaVectorStore(path=path, collection_name=collection_name)
