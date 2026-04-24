import json
import logging
import random
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536

def mock_embedding_api(text: str) -> List[float]:
    """Generates a mock normalized embedding vector."""
    time.sleep(0.05)  # Simulate small delay
    # Generate a random 1536-dimensional vector
    # To make it somewhat "query-like", we could seed it, but random is fine for simulation
    vec = [random.uniform(-1, 1) for _ in range(EMBEDDING_DIM)]
    norm = sum(v**2 for v in vec) ** 0.5
    return [v/norm for v in vec]

def min_max_normalize(scores: np.ndarray) -> np.ndarray:
    """Normalizes an array of scores to the [0, 1] range."""
    min_val = np.min(scores)
    max_val = np.max(scores)
    if max_val - min_val == 0:
        return np.zeros_like(scores)
    return (scores - min_val) / (max_val - min_val)

def hybrid_search(query: str, data: List[Dict[str, Any]], top_k: int = 5, alpha: float = 0.5) -> List[Dict[str, Any]]:
    """
    Simulates a hybrid search combining BM25 and KNN (Cosine Similarity).
    
    Args:
        query: The search query string.
        data: List of chunk dictionaries containing 'text' and 'embedding'.
        top_k: Number of results to return.
        alpha: Weight for KNN score (1-alpha is weight for BM25).
        
    Returns:
        Top K results with combined scores.
    """
    logger.info(f"Executing hybrid search for query: '{query}'")
    
    # 1. Prepare BM25
    tokenized_corpus = [chunk["text"].lower().split() for chunk in data]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    
    # 2. Prepare KNN
    query_embedding = np.array(mock_embedding_api(query))
    chunk_embeddings = np.array([chunk["embedding"] for chunk in data])
    
    # Compute Cosine Similarity (assuming all vectors are normalized)
    knn_scores = np.dot(chunk_embeddings, query_embedding)
    
    # 3. Normalize scores
    normalized_bm25 = min_max_normalize(np.array(bm25_scores))
    normalized_knn = min_max_normalize(knn_scores)
    
    # 4. Combine scores
    combined_scores = alpha * normalized_knn + (1 - alpha) * normalized_bm25
    
    # 5. Get Top K
    top_indices = np.argsort(combined_scores)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        results.append({
            "doc_id": data[idx]["doc_id"],
            "chunk_idx": data[idx]["chunk_idx"],
            "text": data[idx]["text"][:150] + "...",  # Truncate for display
            "combined_score": float(combined_scores[idx]),
            "bm25_score": float(normalized_bm25[idx]),
            "knn_score": float(normalized_knn[idx])
        })
        
    return results

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    data_file = project_root / "experiments" / "exp_002_embeddings" / "results" / "embedded_chunks.json"
    
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        exit(1)
        
    logger.info("Loading embedded chunks...")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    logger.info(f"Loaded {len(data)} chunks.")
    
    queries = [
        "How does Dynamo handle vector clocks and conflict resolution?",
        "What is the architecture of a Bigtable tablet server?"
    ]
    
    for q in queries:
        print(f"\n--- Query: {q} ---")
        results = hybrid_search(q, data, top_k=3)
        for i, res in enumerate(results):
            print(f"{i+1}. [Score: {res['combined_score']:.4f}] {res['doc_id']} (Chunk {res['chunk_idx']})")
            print(f"   BM25: {res['bm25_score']:.4f} | KNN: {res['knn_score']:.4f}")
            print(f"   Text: {res['text']}\n")
